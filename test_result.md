#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Build RAX AI - advanced ChatGPT-style multi-modal AI app (chat/image/voice/file analysis),
  with subscriptions (Stripe Live), admin panel, support, mini-game, multi-language support.

frontend:
  - task: "Multi-language (i18n) support for 5 languages (ES, EN, HI, ZH, RU)"
    implemented: true
    working: true
    file: "/app/frontend/src/i18n.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: |
            Implemented LangProvider context with 5 languages. Auto-detects device language via expo-localization.
            Persists choice in AsyncStorage (rax_lang key). Quick language picker (flags) on /login screen.
            Full language settings in /settings. Translated screens: login, splash, tabs layout, chat list,
            chat thread, profile, settings. Backend /chat/send accepts locale parameter and instructs Claude
            to respond in chosen language. Verified visually with screenshots in ES, EN, HI, ZH, RU.

backend:
  - task: "Chat endpoint accepts locale and instructs AI to respond in user language"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: "Added prefer-locale-over-language logic in chat_send. lang_names dict drives system_prompt directive."

  - task: "Cámara Mágica (AR Lens) - POST /api/lens/scan"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "testing"
          comment: |
            Tested end-to-end with admin user (pro plan). Returns 200 with {result, used_today, limit}.
            Claude Sonnet 4.5 vision analyzes the image and produces Markdown structured output.
            Limit correctly reported as 99999 for pro plan. Quota counter increments correctly.
            Note: backend returns 500 if image is too small (1x1 px) because Anthropic vision rejects with
            "Could not process image". Test confirmed with a valid 256x256 JPEG (works perfectly).
            Auth required: returns 401 without bearer token.

  - task: "Modo Roast - POST /api/roast"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "testing"
          comment: |
            Tested with intensity="medio" using a valid 256x256 JPEG. Returns 200 with
            {roast, intensity, used_today, limit}. Roast text is generated by Claude vision.
            Limit=99999 for pro plan. Auth required: returns 401 without token.
            Same caveat as lens: tiny invalid images (e.g., 1x1) cause Anthropic to refuse;
            backend correctly surfaces 500 with friendly detail.

  - task: "Diario Inteligente - /api/journal/{entry,history,insights,delete}"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "testing"
          comment: |
            All 4 journal endpoints verified:
            - POST /api/journal/entry → 200, returns entry_id + ai_insight (Claude reflection).
            - GET /api/journal/history → 200, returns array including the new entry.
            - GET /api/journal/insights → 200, returns {summary, mood_counts, total}.
            - DELETE /api/journal/entry/{id} → 200, returns {ok: true}. Verified entry no longer in history.
            Auth required: all return 401 without bearer token.

  - task: "Personal Shopper - POST /api/shopper/recommend"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "testing"
          comment: |
            Tested with query="Audífonos inalámbricos bajo $100" + budget_usd=100. Returns 200 with
            {recommendations, used_today, limit}. Uses DuckDuckGo/Bing web search (do_web_search) and
            Claude Sonnet 4.5 to compose Markdown recommendations (~3K chars). limit=99999 for pro plan.
            Quota increments. Auth required: returns 401 without token.

metadata:
  created_by: "main_agent"
  version: "1.3"
  test_sequence: 4
  run_ui: false

test_plan:
  current_focus: []
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    - agent: "main"
      message: |
        SESSION 2: Added 4 killer differentiator features in /studio tab hub:
        - 📸 Cámara Mágica (AR Lens) — /lens — scans anything via Claude Vision
        - 🌙 Diario Inteligente — /journal — persistent memory + weekly insights
        - 🔥 Modo Roast — /roast — 3 intensity levels, sharing
        - 🛍️ Personal Shopper IA — /shopper — products + web search + budget
        Backend: 4 quota-limited endpoints (free=3/day, premium=30/day, pro=∞).
        Frontend: /studio hub with gradient cards, expo-clipboard added for sharing.
        app.json: bundleIdentifier=com.sarangocabrera.raxai, slug=rax-ai, ready for EAS Build.
        Visually verified: studio, journal, roast screens. Lens & shopper not screenshot but identical pattern.
        Pending: App Store publishing guide (to be delivered to user as next step).
    - agent: "testing"
      message: |
        All 4 new features tested end-to-end with admin user (pro plan, limit=99999):
        ✅ POST /api/lens/scan — 200, returns {result, used_today, limit}
        ✅ POST /api/roast — 200, returns {roast, intensity, used_today, limit}
        ✅ POST /api/journal/entry, GET /api/journal/history, GET /api/journal/insights, DELETE /api/journal/entry/{id} — all 200
        ✅ POST /api/shopper/recommend — 200, returns {recommendations, used_today, limit} (web search + Claude)
        ✅ Auth gating verified — all 6 endpoints return 401 without bearer token
        ✅ Pro plan limit=99999 confirmed on all 3 quota-limited endpoints
        Note: lens and roast endpoints require a real image (>=64x64). Anthropic vision API
        refuses 1x1 dummy images with "Could not process image" → backend returns 500.
        This is expected behaviour; real uploads from the app will be normal-sized photos.
        Test script: /app/backend_test.py — 15/15 passing.
