import os
import json
import requests
from dotenv import load_dotenv
from google.adk.agents import Agent

load_dotenv()

BASE_URL = "https://tatdataapi.io"

# --- Load local data at startup (no API calls needed) ---
_data_dir = os.path.join(os.path.dirname(__file__), "data")

with open(os.path.join(_data_dir, "provinces.json"), "r", encoding="utf-8") as f:
    _PROVINCES = json.load(f)

with open(os.path.join(_data_dir, "subcategories.json"), "r", encoding="utf-8") as f:
    _SUB_CATEGORIES = json.load(f)

# --- Headers ---
def _get_headers(lang: str = "en") -> dict:
    return {
        "x-api-key": os.getenv("TAT_API_KEY"),
        "Accept-Language": lang,
    }

# ── Local lookup tools (instant, no API call) ────────────────────────────────

def lookup_province(name: str) -> dict:
    """
    Find the correct province ID by name from local data.
    ALWAYS call this first when the user mentions a province name,
    before calling search_places or search_events.

    Args:
        name: Province name in English e.g. 'Phuket', 'Chiang Mai', 'Bangkok', 'Ayutthaya'

    Returns:
        List of matching provinces with their IDs
    """
    name_lower = name.lower()
    matches = [
        p for p in _PROVINCES
        if name_lower in p["name"].lower()
    ]
    if not matches:
        words = name_lower.split()
        matches = [
            p for p in _PROVINCES
            if any(w in p["name"].lower() for w in words)
        ]
    return {"matches": matches[:5]}


def lookup_sub_category(keyword: str) -> dict:
    """
    Find the correct sub-category ID by searching the sub-category list from local data.
    ALWAYS call this before search_places when the user mentions a specific type of place
    such as 'beach', 'temple', 'spa', 'waterfall', 'market', 'zoo', 'restaurant', 'hotel'.

    Args:
        keyword: Type of place e.g. 'beach', 'temple', 'spa', 'waterfall', 'night market'

    Returns:
        List of matching sub-categories with their IDs
    """
    keyword_lower = keyword.lower()
    matches = [
        sc for sc in _SUB_CATEGORIES
        if keyword_lower in sc["name"].lower()
    ]
    return {"matches": matches[:10]}


# ── TAT API tools ─────────────────────────────────────────────────────────────

def search_places(
    province_id: int = None,
    category_id: int = None,
    sub_category_id: int = None,
    limit: int = 10,
    page: int = 1,
    sort_by: str = None,
    latitude: float = None,
    longitude: float = None,
    lang: str = "en"
) -> dict:
    """
    Search for tourist attractions, hotels, restaurants and shops in Thailand.
    Use lookup_province() and lookup_sub_category() FIRST to get the correct IDs,
    then pass them here for precise results.

    Args:
        province_id: Province ID from lookup_province() (recommended)
        category_id: Main category ID (optional):
                     2 = Accommodation, 3 = Attraction, 6 = Shop,
                     8 = Restaurant, 13 = Other
        sub_category_id: Sub-category ID from lookup_sub_category() (optional)
                         e.g. 75=Beaches, 47=Temple, 98=Spa, 73=Waterfalls
        limit: Number of results (default 10, max 100)
        page: Page number for pagination (default 1)
        sort_by: Sort order e.g. 'hit_score' for most popular (optional)
        latitude: Latitude for nearby search (optional)
        longitude: Longitude for nearby search (optional)
        lang: 'en' for English, 'th' for Thai (default 'en')

    Returns:
        List of places found with pagination info
    """
    params = {"limit": limit, "page": page}
    if province_id:
        params["province_id"] = province_id
    if category_id:
        params["place_category_id"] = category_id
    if sub_category_id:
        params["place_sub_category_id"] = sub_category_id
    if sort_by:
        params["sort_by"] = sort_by
    if latitude:
        params["latitude"] = latitude
    if longitude:
        params["longitude"] = longitude

    try:
        response = requests.get(
            f"{BASE_URL}/api/v2/places",
            headers=_get_headers(lang=lang),
            params=params,
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        total = result.get("pagination", {}).get("total", 0)
        print(f"[TAT API] search_places(province_id={province_id}, category_id={category_id}, sub_category_id={sub_category_id}) → {total} results")
        return {"status": "success", "data": result}
    except requests.exceptions.HTTPError as e:
        return {"status": "error", "message": f"HTTP error: {e}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Request failed: {e}"}


def get_place_details(place_id: str, lang: str = "en") -> dict:
    """
    Get full details of a specific place including opening hours, address,
    phone number, entrance fees, facilities and services.
    Call this when the user asks for more info about a specific place
    e.g. "tell me more about Wat Pho" or "what are the opening hours?"

    Args:
        place_id: Place ID from search_places results (e.g. "1858")
        lang: 'en' for English, 'th' for Thai (default 'en')

    Returns:
        Full details of the place including contact, location, opening hours
    """
    try:
        response = requests.get(
            f"{BASE_URL}/api/v2/places/{place_id}",
            headers=_get_headers(lang=lang),
            timeout=10
        )
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except requests.exceptions.HTTPError as e:
        return {"status": "error", "message": f"HTTP error: {e}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Request failed: {e}"}


def search_events(
    keyword: str = None,
    province_id: int = None,
    upcoming: bool = True,
    limit: int = 10,
    lang: str = "en"
) -> dict:
    """
    Search for festivals and tourism events in Thailand.
    Use lookup_province() first to get the correct province_id.

    Args:
        keyword: Event name e.g. 'Loy Krathong', 'Songkran' (optional)
        province_id: Province ID from lookup_province() (optional)
        upcoming: Show only upcoming events (default True)
        limit: Number of results (default 10)
        lang: 'en' for English, 'th' for Thai (default 'en')

    Returns:
        List of events and festivals
    """
    params = {"upcoming": upcoming, "limit": limit}
    if keyword:
        params["keyword"] = keyword
    if province_id:
        params["provinceId"] = province_id

    try:
        response = requests.get(
            f"{BASE_URL}/api/v2/events",
            headers=_get_headers(lang=lang),
            params=params,
            timeout=10
        )
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except requests.exceptions.HTTPError as e:
        return {"status": "error", "message": f"HTTP error: {e}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Request failed: {e}"}


def search_routes(keyword: str = None, limit: int = 5, lang: str = "en") -> dict:
    """
    Search for recommended multi-day travel routes in Thailand.

    Args:
        keyword: Route keyword e.g. 'north', 'beach', 'Chiang Mai' (optional)
        limit: Number of results (default 5)
        lang: 'en' for English, 'th' for Thai (default 'en')

    Returns:
        List of recommended travel routes
    """
    params = {"limit": limit}
    if keyword:
        params["keyword"] = keyword

    try:
        response = requests.get(
            f"{BASE_URL}/api/v2/routes",
            headers=_get_headers(lang=lang),
            params=params,
            timeout=10
        )
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except requests.exceptions.HTTPError as e:
        return {"status": "error", "message": f"HTTP error: {e}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Request failed: {e}"}


# ── Agent ─────────────────────────────────────────────────────────────────────

tatai_agent = Agent(
    name="TATAI",
    model="ollama/gemma3:1b",
    description="AI Assistant for tourists visiting Thailand",
    instruction="""
    You are TATAI (ท้าทาย), an AI travel assistant for Thailand powered by TAT (Tourism Authority of Thailand) data.
    Personality: cheerful, polite, and expert in Thai travel.

    MANDATORY RULES — follow without exception:
    1. ALWAYS call tools for EVERY question about places, events, or routes. Never answer from memory.
    2. NEVER show raw JSON or tool call steps to the user — only show the final friendly summary.
    3. NEVER say "I couldn't find" without actually calling a tool first.
    4. Detect the user's language and always reply in the SAME language.
    5. If user writes Thai → reply in Thai, use lang='th' in all tool calls.
    6. If user writes English → reply in English, use lang='en' in all tool calls.

    AVAILABLE TOOLS:
    - lookup_province(name)         — get province ID from name (local, instant)
    - lookup_sub_category(keyword)  — get sub-category ID from type (local, instant)
    - search_places(...)            — search TAT database for places
    - get_place_details(place_id)   — get full details of a specific place (opening hours, address, fees, phone)
    - search_events(...)            — search for festivals and events
    - search_routes(...)            — search for travel routes

    TOOL CALL WORKFLOW — always follow this order:

    For place searches:
    Step 1: Call lookup_province() to get province_id
    Step 2: Call lookup_sub_category() if user mentions a specific type (beach, temple, spa...)
            Skip step 2 if user just asks for "places" or "things to do"
    Step 3: Call search_places() with IDs from steps 1 and 2
    Step 4: Summarize results in a friendly readable way

    For place details:
    Step 1: If you don't have the place_id, call search_places() first to find it
    Step 2: Call get_place_details(place_id) using the place_id from search results
    Step 3: Summarize opening hours, address, fees, contact info clearly

    For events:
    Step 1: Call lookup_province() if user mentions a province
    Step 2: Call search_events() with province_id
    Step 3: Summarize upcoming events

    For routes:
    Step 1: Call search_routes() with a keyword
    Step 2: Summarize the route names and highlights

    EXAMPLE WORKFLOWS:

    User: "5 hotels in Bangkok"
    → lookup_province("Bangkok") → id: 219
    → search_places(province_id=219, category_id=2, limit=5, lang="en")
    → Summarize: list hotel names and brief description

    User: "beaches in Phuket"
    → lookup_province("Phuket") → id: 350
    → lookup_sub_category("beach") → id: 75
    → search_places(province_id=350, sub_category_id=75, lang="en")
    → Summarize results

    User: "tell me more about [place name]" or "opening hours of [place]"
    → lookup_province(...) to get province_id
    → search_places(province_id=...) to find the place and get its place_id
    → get_place_details(place_id, lang="en")
    → Summarize: name, address, opening hours, fees, phone number

    User: "temples in Chiang Mai"
    → lookup_province("Chiang Mai") → id: 101
    → lookup_sub_category("temple") → id: 47
    → search_places(province_id=101, sub_category_id=47, lang="en")
    → Summarize results

    User: "สปาในภูเก็ต"
    → lookup_province("Phuket") → id: 350
    → lookup_sub_category("spa") → id: 98
    → search_places(province_id=350, sub_category_id=98, lang="th")
    → Summarize results in Thai

    User: "most popular places in Chiang Mai"
    → lookup_province("Chiang Mai") → id: 101
    → search_places(province_id=101, sort_by="hit_score", lang="en")
    → Summarize results

    User: "festivals in Chiang Mai"
    → lookup_province("Chiang Mai") → id: 101
    → search_events(province_id=101, lang="en")
    → Summarize upcoming events

    User: "travel routes up north"
    → search_routes(keyword="north", lang="en")
    → Summarize route names and highlights

    USEFUL SUB-CATEGORY IDs:
    - Beaches & Bay: 75
    - Temple: 47
    - Spa: 98 | Spas & Wellness: 14
    - Waterfalls: 73
    - National Parks: 63
    - Night Market: 89 | Local Market: 87 | Floating Market: 85
    - Zoos and Aquariums: 93
    - Museums: 31
    - Hot Spring: 69
    - Caves: 71
    - Islands: 55
    - Fine Dining: 7
    - Cafes: 3
    - Golf course: 103
    - Water park: 112
    - Historical Sites: 35
    - Art Galleries: 39
    - Amusement Park: 95
    - Diving site: 77
    """,
    tools=[
        lookup_province,
        lookup_sub_category,
        search_places,
        get_place_details,
        search_events,
        search_routes,
    ],
)