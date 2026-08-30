"""Widget API endpoints for public widget interactions."""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.database import get_db
from app.services.project_service import ProjectService
from app.services.visitor_service import VisitorService
from app.services.conversation_service import ConversationService
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    MessageRole,
)
from app.core.exceptions import NotFoundException, ValidationException, AuthenticationException
from app.dependencies.rate_limit import RateLimiter
from app.services.recaptcha_service import verify_recaptcha_token
from app.core.config import settings

router = APIRouter(prefix="/api/widget", tags=["Widget"])

# Define rate limiters
session_limiter = RateLimiter(requests=5, window=60) # 5 sessions per minute per IP
message_limiter = RateLimiter(requests=20, window=60) # 20 messages per minute per IP

def verify_domain_access(request: Request, project):
    """Verify that the request origin matches the project's allowed domains."""
    if not project.allowed_domains:
        return  # No whitelist configured, allow all
        
    origin = request.headers.get("origin") or request.headers.get("referer")
    if not origin:
        raise AuthenticationException("Origin header missing for domain-restricted project")
        
    parsed = urlparse(origin)
    domain = parsed.netloc if parsed.netloc else parsed.path
    
    # Strip port (e.g., localhost:3000 -> localhost)
    domain = domain.split(":")[0].lower()
    
    allowed = [d.lower() for d in project.allowed_domains]
    if domain not in allowed:
        raise AuthenticationException(f"Domain '{domain}' is not whitelisted for this widget")


@router.post(
    "/session",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create widget session",
    description="Initialize a visitor session and conversation for the widget",
)
async def create_widget_session(
    request: Request,
    session_create: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(session_limiter),
):
    """Create a new visitor session and conversation.
    
    This endpoint is called by the embedded widget to:
    1. Validate the project API key
    2. Create or get a visitor
    3. Create a new conversation
    
    Returns safe identifiers for client-side tracking.
    """
    try:
        # Verify reCAPTCHA if configured and not in development
        if settings.recaptcha_site_key and settings.recaptcha_secret_key and settings.environment != "development":
            if not session_create.recaptcha_token:
                raise ValidationException("reCAPTCHA token is required")
            
            is_valid = await verify_recaptcha_token(session_create.recaptcha_token)
            if not is_valid:
                raise AuthenticationException("Invalid reCAPTCHA token")

        # Get project by API key
        project = await ProjectService.get_project_by_api_key(
            session_create.project_api_key, db
        )
        
        if not project:
            raise AuthenticationException("Invalid API key")
            
        verify_domain_access(request, project)
        
        if not project.is_active:
            raise ValidationException("Project is not active")
        
        # Get or create visitor
        visitor = await VisitorService.get_visitor_by_identifier(
            session_create.visitor_identifier, db
        )
        
        if visitor is None:
            # Create new visitor with the provided identifier
            visitor = await VisitorService.get_or_create_visitor(
                project.id,
                visitor_identifier=session_create.visitor_identifier,
                db=db
            )
        else:
            # Update last seen
            visitor = await VisitorService.update_visitor_last_seen(visitor.id, db)
        
        # Create conversation
        conversation = await ConversationService.create_conversation(
            project.id, visitor.id, db
        )
        
        return {
            "visitor_id": str(visitor.id),
            "visitor_identifier": visitor.visitor_identifier,
            "conversation_id": str(conversation.id),
            "created_at": conversation.created_at.isoformat(),
        }
    except (NotFoundException, ValidationException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send message",
    description="Send a user message to the conversation",
)
async def send_message(
    request: Request,
    conversation_id: UUID,
    message_create: MessageCreate,
    project_api_key: str = Query(..., description="Project API key"),
    db: AsyncSession = Depends(get_db),
    _=Depends(message_limiter),
):
    """Send a user message to a conversation.
    
    Query parameter:
    - **project_api_key**: Project API key for validation
    
    The message will be processed by the AI in a separate endpoint.
    """
    try:
        # Get conversation
        conversation = await ConversationService.get_conversation_by_id(
            conversation_id, db
        )
        
        # Verify project API key matches
        project = await ProjectService.get_project_by_api_key(project_api_key, db)
        
        if not project or project.id != conversation.project_id:
            raise AuthenticationException("Invalid API key for this conversation")
            
        verify_domain_access(request, project)
        
        if conversation.status != "active":
            raise ValidationException("Conversation is not active")
        
        # Add user message
        message = await ConversationService.add_message(
            conversation_id,
            MessageRole.USER,
            message_create.content,
            db,
        )
        
        return MessageResponse.model_validate(message)
    except (NotFoundException, ValidationException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="Get conversation messages",
    description="Retrieve message history from a conversation",
)
async def get_messages(
    request: Request,
    conversation_id: UUID,
    project_api_key: str = Query(..., description="Project API key"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(message_limiter),
):
    """Get message history from a conversation.
    
    Query parameters:
    - **project_api_key**: Project API key for validation
    - **limit**: Maximum number of messages to return (1-100, default 20)
    """
    try:
        # Get conversation
        conversation = await ConversationService.get_conversation_by_id(
            conversation_id, db
        )
        
        # Verify project API key matches
        project = await ProjectService.get_project_by_api_key(project_api_key, db)
        
        if not project or project.id != conversation.project_id:
            raise AuthenticationException("Invalid API key for this conversation")
            
        verify_domain_access(request, project)
        
        # Get messages
        messages = await ConversationService.get_conversation_messages(
            conversation_id, db, limit=limit
        )
        
        return [MessageResponse.model_validate(msg) for msg in messages]
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )


@router.get(
    "/script.js",
    summary="Get embeddable widget script",
    description="Generate ready-to-use JavaScript code for embedding interactive AI chat widget into any website",
)
async def get_widget_script(
    request: Request,
    api_key: str = Query(..., description="Project API Key"),
    db: AsyncSession = Depends(get_db),
):
    """Serve the complete dynamic JavaScript script for embedding the chatbot widget."""
    from fastapi.responses import Response

    project = await ProjectService.get_project_by_api_key(api_key, db)
    if not project or not project.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or inactive",
        )
        
    try:
        verify_domain_access(request, project)
    except AuthenticationException as e:
        raise HTTPException(status_code=403, detail=str(e))

    safe_name = project.name.replace('"', '').replace('\n', ' ')
    safe_msg = (project.welcome_message or 'Hello! How can I assist you today?').replace('"', '').replace('\n', ' ')
    backend_url = str(request.base_url).rstrip('/')

    script_content = f"""(function() {{
  if (window.__FLYRANK_WIDGET_LOADED__) return;
  window.__FLYRANK_WIDGET_LOADED__ = true;

  // Load ReCAPTCHA dynamically if configured
  if ("{settings.recaptcha_site_key}") {{
    var script = document.createElement('script');
    script.src = "https://www.google.com/recaptcha/api.js?render={settings.recaptcha_site_key}";
    document.head.appendChild(script);
  }}


  var API_KEY = "{project.api_key}";
  var PROJECT_NAME = "{safe_name}";
  var WELCOME_MSG = "{safe_msg}";
  var BACKEND_URL = "{backend_url}";
  var THEME_COLOR = "{project.theme_color or '#7c3aed'}";

  function getContrastColor(hexcolor) {{
    if (!hexcolor) return "#ffffff";
    hexcolor = hexcolor.replace("#", "");
    if (hexcolor.length === 3) {{
      hexcolor = hexcolor.split("").map(function(hex) {{ return hex + hex; }}).join("");
    }}
    if (hexcolor.length !== 6) return "#ffffff";
    var r = parseInt(hexcolor.substr(0, 2), 16);
    var g = parseInt(hexcolor.substr(2, 2), 16);
    var b = parseInt(hexcolor.substr(4, 2), 16);
    var yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
    return (yiq >= 128) ? "#000000" : "#ffffff";
  }}
  var TEXT_ON_THEME = getContrastColor(THEME_COLOR);

  var visitorIdentifier = localStorage.getItem("flyrank_vis_id") || ("vis_" + Math.random().toString(36).substring(2, 15));
  localStorage.setItem("flyrank_vis_id", visitorIdentifier);
  var conversationId = null;

  var container = document.createElement("div");
  container.id = "flyrank-widget-root";
  container.style.position = "fixed";
  container.style.bottom = "24px";
  container.style.right = "24px";
  container.style.zIndex = "2147483647";
  container.style.fontFamily = "system-ui, -apple-system, sans-serif";

  var style = document.createElement("style");
  style.textContent = `
    #flyrank-launcher {{
      width: 60px; height: 60px; border-radius: 50%;
      background: ` + THEME_COLOR + `;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
      display: flex; align-items: center; justify-content: center;
      cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;
    }}
    #flyrank-launcher:hover {{ transform: scale(1.05); box-shadow: 0 10px 28px rgba(0, 0, 0, 0.3); }}
    #flyrank-window {{
      display: none; width: 350px; height: 500px; max-height: 80vh; max-width: 90vw; border-radius: 16px;
      background: #0f172a; border: 1px solid #1e293b;
      box-shadow: 0 20px 40px rgba(0,0,0,0.5);
      flex-direction: column; overflow: hidden; margin-bottom: 16px;
    }}
    #flyrank-header {{
      padding: 14px 16px; background: ` + THEME_COLOR + `; color: ` + TEXT_ON_THEME + `;
      display: flex; align-items: center; justify-content: space-between; font-weight: 600;
    }}
    #flyrank-body {{
      flex: 1; padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; background: #0b0f19;
    }}
    .flyrank-msg {{
      max-width: 80%; padding: 10px 14px; border-radius: 14px; font-size: 14px; line-height: 1.4; word-wrap: break-word; white-space: pre-wrap;
    }}
    .flyrank-msg-bot {{ background: #1e293b; color: #f1f5f9; align-self: flex-start; border: 1px solid #334155; }}
    .flyrank-msg-user {{ background: ` + THEME_COLOR + `; color: ` + TEXT_ON_THEME + `; align-self: flex-end; }}
    #flyrank-footer {{
      padding: 12px; background: #0f172a; border-top: 1px solid #1e293b; display: flex; gap: 8px;
    }}
    #flyrank-input {{
      flex: 1; padding: 10px 14px; border-radius: 10px; border: 1px solid #334155;
      background: #1e293b; color: #fff; font-size: 14px; outline: none;
    }}
    #flyrank-input:focus {{ border-color: ` + THEME_COLOR + `; }}
    #flyrank-send-btn {{
      padding: 0 16px; border-radius: 10px; background: ` + THEME_COLOR + `; color: ` + TEXT_ON_THEME + `; border: none; font-weight: 600; cursor: pointer;
    }}
  `;
  document.head.appendChild(style);

  container.innerHTML = `
    <div id="flyrank-window">
      <div id="flyrank-header">
        <span>` + PROJECT_NAME + `</span>
        <span id="flyrank-close-btn" style="cursor:pointer;font-size:18px;">✕</span>
      </div>
      <div id="flyrank-body"></div>
      <div id="flyrank-footer">
        <input id="flyrank-input" placeholder="Type a message..." />
        <button id="flyrank-send-btn">Send</button>
      </div>
    </div>
    <div id="flyrank-launcher">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
    </div>
  `;
  document.body.appendChild(container);

  var launcher = document.getElementById("flyrank-launcher");
  var chatWindow = document.getElementById("flyrank-window");
  var closeBtn = document.getElementById("flyrank-close-btn");
  var body = document.getElementById("flyrank-body");
  var input = document.getElementById("flyrank-input");
  var sendBtn = document.getElementById("flyrank-send-btn");

  function appendMessage(text, role) {{
    var msg = document.createElement("div");
    msg.className = "flyrank-msg " + (role === "user" ? "flyrank-msg-user" : "flyrank-msg-bot");
    msg.textContent = text;
    body.appendChild(msg);
    body.scrollTop = body.scrollHeight;
  }}

  async function initSession() {{
    try {{
      var payload = {{ project_api_key: API_KEY, visitor_identifier: visitorIdentifier }};
      
      // Handle ReCAPTCHA if enabled
      if (window.grecaptcha && "{settings.recaptcha_site_key}") {{
        try {{
          var token = await new Promise((resolve, reject) => {{
            grecaptcha.ready(function() {{
              try {{
                grecaptcha.execute("{settings.recaptcha_site_key}", {{action: 'submit'}})
                  .then(resolve)
                  .catch(reject);
              }} catch (err) {{
                reject(err);
              }}
            }});
          }});
          payload.recaptcha_token = token;
        }} catch(e) {{
          console.error("ReCAPTCHA failed", e);
        }}
      }}

      var res = await fetch(BACKEND_URL + "/api/widget/session", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload)
      }});
      var data = await res.json();
      if (data && data.conversation_id) {{
        conversationId = data.conversation_id;
        appendMessage(WELCOME_MSG, "assistant");
      }} else {{
        console.error("Failed to start session:", data);
        appendMessage("Sorry, we couldn't start the chat session. Please try again later.", "bot");
      }}
    }} catch (e) {{
      console.error("Failed to initialize widget session", e);
      appendMessage("Sorry, we couldn't connect to the server.", "bot");
    }}
  }}
  async function sendMessage() {{
    var text = input.value.trim();
    if (!text || !conversationId) return;
    appendMessage(text, "user");
    input.value = "";

    try {{
      var res = await fetch(BACKEND_URL + "/api/chat/send?conversation_id=" + conversationId + "&project_api_key=" + API_KEY, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ content: text }})
      }});

      if (!res.ok) throw new Error("Failed to send message");

      var reader = res.body.getReader();
      var decoder = new TextDecoder("utf-8");
      
      var botMsg = document.createElement("div");
      botMsg.className = "flyrank-msg flyrank-msg-bot";
      body.appendChild(botMsg);

      var buffer = "";
      while (true) {{
        var {{ value, done }} = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, {{ stream: true }});
        var events = buffer.split('\\n\\n');
        buffer = events.pop();
        
        for (var i = 0; i < events.length; i++) {{
          var ev = events[i];
          if (ev.startsWith("data: ")) {{
            var dataStr = ev.substring(6);
            if (dataStr) {{
              try {{
                var data = JSON.parse(dataStr);
                if (data.error) {{
                  botMsg.textContent = "Error: " + data.error;
                  body.scrollTop = body.scrollHeight;
                }} else if (data.chunk !== undefined) {{
                  botMsg.textContent += data.chunk;
                  body.scrollTop = body.scrollHeight;
                }}
              }} catch (e) {{
                console.error("Error parsing chunk", e, dataStr);
              }}
            }}
          }}
        }}
      }}
    }} catch(err) {{
      console.error("Error sending message", err);
      appendMessage("Sorry, an error occurred. Please try again.", "bot");
    }}
  }}

  launcher.addEventListener("click", function() {{
    var isHidden = chatWindow.style.display === "none" || chatWindow.style.display === "";
    chatWindow.style.display = isHidden ? "flex" : "none";
    if (isHidden && !conversationId) {{
      initSession();
    }}
  }});

  closeBtn.addEventListener("click", function() {{
    chatWindow.style.display = "none";
  }});

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", function(e) {{
    if (e.key === "Enter") sendMessage();
  }});
}})();"""
    return Response(content=script_content, media_type="application/javascript")

