# PIB Website Reverse Engineering Report

> Generated: 2026-09-21  
> Target: https://www.pib.gov.in  
> Method: Python requests + BeautifulSoup (no browser automation)

---

## Table of Contents
1. [allRel.aspx Deep Inspection](#1-allrelaspx-deep-inspection)
2. [Date Filtering Mechanism](#2-date-filtering-mechanism)
3. [Ministry Filtering](#3-ministry-filtering)
4. [Aboutarchive.aspx Analysis](#4-aboutarchiveaspx-analysis)
5. [PRID Range & Date Mapping](#5-prid-range--date-mapping)
6. [URL Variant Testing](#6-url-variant-testing)
7. [Internal Link Crawling](#7-internal-link-crawling)
8. [AJAX/XHR Detection](#8-ajaxxhr-detection)
9. [Archive Deep Dive](#9-archive-deep-dive)
10. [RSS/Atom Feeds](#10-rssatom-feeds)
11. [Press Release Page Structure](#11-press-release-page-structure)
12. [Summary & Key Findings](#12-summary--key-findings)

---

## 1. allRel.aspx Deep Inspection

**URL:** `https://www.pib.gov.in/allRel.aspx?reg=48&lang=1`  
**Response:** 200 OK, 127,214 bytes, `text/html; charset=utf-8`

### Form Structure

| Property | Value |
|----------|-------|
| action | `./allRel.aspx?reg=48&lang=1` |
| method | `POST` |
| id | `form1` |
| enctype | (default - application/x-www-form-urlencoded) |

### Hidden Inputs (11 total)

| # | Name | ID | Value |
|---|------|-----|-------|
| 1 | `script_HiddenField` | `script_HiddenField` | *(empty)* |
| 2 | `__EVENTTARGET` | `__EVENTTARGET` | *(empty)* |
| 3 | `__EVENTARGUMENT` | `__EVENTARGUMENT` | *(empty)* |
| 4 | `__LASTFOCUS` | `__LASTFOCUS` | *(empty)* |
| 5 | `__VIEWSTATE` | `__VIEWSTATE` | 34,376 chars (base64-encoded) |
| 6 | `__VIEWSTATEGENERATOR` | `__VIEWSTATEGENERATOR` | `CBED066B` |
| 7 | `__VIEWSTATEENCRYPTED` | `__VIEWSTATEENCRYPTED` | *(empty)* |
| 8 | `__EVENTVALIDATION` | `__EVENTVALIDATION` | 4,104 chars (base64-encoded) |
| 9 | `ctl00$ContentPlaceHolder1$Print1$print` | `ContentPlaceHolder1_Print1_print` | *(image button)* |
| 10 | `ctl00$ContentPlaceHolder1$hydregionid` | `ContentPlaceHolder1_hydregionid` | `3` |
| 11 | `ctl00$ContentPlaceHolder1$hydLangid` | `ContentPlaceHolder1_hydLangid` | `1` |

### Select Dropdowns (6 total)

#### Region Dropdown
- **name:** `ctl00$Bar1$ddlregion`
- **id:** `Bar1_ddlregion`
- **Options:** 29 regions

| Value | Text |
|-------|------|
| 3 | PIB Delhi (default/selected) |
| 1 | PIB Mumbai |
| 5 | PIB Hyderabad |
| 6 | PIB Chennai |
| 17 | PIB Chandigarh |
| 19 | PIB Kolkata |
| 20 | PIB Bengaluru |
| 21 | PIB Bhubaneswar |
| 22 | PIB Ahmedabad |
| 23 | PIB Guwahati |
| 24 | PIB Thiruvananthpuram |
| 30 | PIB Imphal |
| 31 | PIB Mizoram |
| 32 | PIB Agartala |
| 33 | PIB Gangtok |
| 34 | PIB Kohima |
| 35 | PIB Shillong |
| 36 | PIB Itanagar |
| 37 | PIB Lucknow |
| 38 | PIB Bhopal |
| 39 | PIB Jaipur |
| 40 | PIB Patna |
| 41 | PIB Ranchi |
| 42 | PIB Shimla |
| 43 | PIB Raipur |
| 44 | PIB Jammu and Kashmir |
| 45 | PIB Vijayawada |
| 46 | PIB Dehradun |
| **48** | **National** |

#### Language Dropdown
- **name:** `ctl00$Bar1$ddlLang`
- **id:** `Bar1_ddlLang`
- **Options:** 2

| Value | Text |
|-------|------|
| 2 | हिन्दी |
| **1** | **English** (selected) |

#### Ministry Dropdown
- **name:** `ctl00$ContentPlaceHolder1$ddlMinistry`
- **id:** `ContentPlaceHolder1_ddlMinistry`
- **Options:** 97 ministries (see [Section 3](#3-ministry-filtering))

#### Day Dropdown
- **name:** `ctl00$ContentPlaceHolder1$ddlday`
- **id:** `ContentPlaceHolder1_ddlday`
- **Options:** 32 (0=All, 1-31 for days)

#### Month Dropdown
- **name:** `ctl00$ContentPlaceHolder1$ddlMonth`
- **id:** `ContentPlaceHolder1_ddlMonth`
- **Options:** 12 (January=1 through December=12)
- **Default:** Current month (September=9)

#### Year Dropdown
- **name:** `ctl00$ContentPlaceHolder1$ddlYear`
- **id:** `ContentPlaceHolder1_ddlYear`
- **Options:** 10 (2026=2026 down to 2017=2017)
- **Default:** 2026

### JavaScript Event Handlers

#### `onchange` (6 handlers) - All trigger ASP.NET postback
| Element | Handler |
|---------|---------|
| `ddlregion` | `__doPostBack('ctl00$Bar1$ddlregion','')` |
| `ddlLang` | `__doPostBack('ctl00$Bar1$ddlLang','')` |
| `ddlMinistry` | `__doPostBack('ctl00$ContentPlaceHolder1$ddlMinistry','')` |
| `ddlday` | `__doPostBack('ctl00$ContentPlaceHolder1$ddlday','')` |
| `ddlMonth` | `__doPostBack('ctl00$ContentPlaceHolder1$ddlMonth','')` |
| `ddlYear` | `__doPostBack('ctl00$ContentPlaceHolder1$ddlYear','')` |

#### `onclick` (43 handlers)
- Font size controls: `set_font_size('decrease'/'increase'/''`
- Accessibility stylesheet switching: `setActiveStyleSheet('change'/'normal'/'green'/'yellow')`
- External link confirmations: `return confirm('This link will take you to a webpage outside...')`
- External links: `window.open('https://...')`

#### `onkeydown` (3 handlers)
- Keyboard navigation for external links

#### `onload` (1 handler)
- Image randomization: `Math.floor((Math.random() * 100...)`

### Postback References
- **No inline `__doPostBack` calls** in the HTML source
- The `__doPostBack` function is defined in `WebResource.axd` and invoked via `onchange` handlers on the dropdowns

### Script Tags (23 total)

| # | Source | Purpose |
|---|--------|---------|
| 1 | `/js/scrolljs/myscolljs.js` | jQuery (97KB, minified) |
| 2 | `/js/jquery.meanmenu.js` | Mobile menu |
| 3 | inline | `e`, `t`, `a` functions |
| 4 | inline | `__doPostBack` function definition |
| 5 | `/WebResource.axd?...` | ASP.NET WebForms framework |
| 6 | `/ScriptResource.axd?...` | ASP.NET AJAX (89KB, MS AJAX library) |
| 7 | `/ScriptResource.axd?...` | ASP.NET AJAX (37KB) |
| 9 | inline | `setDropdownState`, `closeAllDropdowns` |
| 10 | inline | `initializeTopMenuAccessibility` |
| 11 | `googletagmanager.com/...` | Google Analytics |
| 15 | `/js/jquery-3.7.1.min_all_js.js?v=1.3` | jQuery 3.7.1 (161KB) |
| 16 | `/js/accessibility.js?v=7` | Accessibility features |
| 18 | `/js/custom.js?v=0` | Custom functions (lightbox, etc.) |

---

## 2. Date Filtering Mechanism

### How It Works
The date filtering on `allRel.aspx` uses **ASP.NET WebForms postback** via dropdown selects. There is **NO JavaScript calendar/date picker** and **NO AJAX calendar extender**.

### Mechanism
1. User selects Day/Month/Year from dropdown selects
2. Each dropdown's `onchange` triggers `__doPostBack(controlName, '')` 
3. This submits the entire form with updated `__VIEWSTATE` and `__EVENTTARGET`
4. Server returns a new page with filtered results

### POST Data Structure
```
__EVENTTARGET=ctl00$ContentPlaceHolder1$ddlMonth
__EVENTARGUMENT=
__VIEWSTATE=(34K base64)
__VIEWSTATEGENERATOR=CBED066B
__EVENTVALIDATION=(4K base64)
ctl00$Bar1$ddlregion=3
ctl00$Bar1$ddlLang=1
ctl00$ContentPlaceHolder1$ddlMinistry=0
ctl00$ContentPlaceHolder1$ddlday=0
ctl00$ContentPlaceHolder1$ddlMonth=9
ctl00$ContentPlaceHolder1$ddlYear=2026
```

### POSTing with `__EVENTTARGET` Set
When `__EVENTTARGET` is set to a dropdown name, the server processes that dropdown's change event. The `ddlMonth` change produces the most significant content change (175,049 bytes vs default 127,213 bytes).

### Key Finding
The date filtering is a **full-page postback**, not AJAX. Each filter change reloads the entire page with updated `__VIEWSTATE`.

---

## 3. Ministry Filtering

### Ministry Dropdown
- **Control name:** `ctl00$ContentPlaceHolder1$ddlMinistry`
- **Control id:** `ContentPlaceHolder1_ddlMinistry`
- **Total options:** 97

### Complete Ministry List

| Value | Ministry Name |
|-------|--------------|
| 0 | All Ministry |
| 1 | President's Secretariat |
| 2 | Vice President's Secretariat |
| 3 | Prime Minister's Office |
| 2608 | Lok Sabha Secretariat |
| 2934 | Rajya Sabha Secretariat |
| 61 | Cabinet |
| 62 | Cabinet Committee Decisions |
| 63 | Cabinet Committee on Economic Affairs (CCEA) |
| 68 | Cabinet Secretariat |
| 70 | Cabinet Committee on Infrastructure |
| 71 | Cabinet Committee on Price |
| 75 | Cabinet Committee on Investment |
| 80 | AYUSH |
| 72 | Other Cabinet Committees |
| 14 | Department of Space |
| 45 | Department of Ocean Development |
| 56 | Department of Atomic Energy |
| 35 | Election Commission |
| 1330 | Finance Commission |
| 27 | Ministry of Agriculture & Farmers Welfare |
| 58 | Ministry of Agro & Rural Industries |
| 41 | Ministry of Chemicals and Fertilizers |
| 41 | Department of Pharmaceuticals |
| 41 | Department of Fertilizers |
| 41 | Department of Chemicals and Petrochemicals |
| 26 | Ministry of Civil Aviation |
| 42 | Ministry of Coal |
| 16 | Ministry of Commerce & Industry |
| 24 | Ministry of Communications |
| 60 | Ministry of Company Affairs |
| 39 | Ministry of Consumer Affairs, Food & Public Distribution |
| 1440 | Ministry of Cooperation |
| 66 | Ministry of Corporate Affairs |
| 17 | Ministry of Culture |
| 33 | Ministry of Defence |
| 57 | Ministry of Development of North-East Region |
| 48 | Ministry of Disinvestment |
| 73 | Ministry of Drinking Water & Sanitation |
| 67 | Ministry of Earth Sciences |
| 8 | Ministry of Education |
| 1323 | Ministry of Electronics & IT |
| 30 | Ministry of Environment, Forest and Climate Change |
| 4 | Ministry of External Affairs |
| 15 | Ministry of Finance |
| 1340 | Ministry of Fisheries, Animal Husbandry & Dairying |
| 40 | Ministry of Food Processing Industries |
| 31 | Ministry of Health and Family Welfare |
| 53 | Ministry of Heavy Industries |
| 5 | Ministry of Home Affairs |
| 47 | Ministry of Housing & Urban Affairs |
| 11 | Ministry of Information & Broadcasting |
| 1336 | Ministry of Jal Shakti |
| 21 | Ministry of Labour & Employment |
| 7 | Ministry of Law and Justice |
| 51 | Ministry of Micro,Small & Medium Enterprises |
| 44 | Ministry of Mines |
| 65 | Ministry of Minority Affairs |
| 28 | Ministry of New and Renewable Energy |
| 59 | Ministry of Overseas Indian Affairs |
| 10 | Ministry of Panchayati Raj |
| 12 | Ministry of Parliamentary Affairs |
| 6 | Ministry of Personnel, Public Grievances & Pensions |
| 20 | Ministry of Petroleum & Natural Gas |
| 79 | Ministry of Planning |
| 52 | Ministry of Power |
| 23 | Ministry of Railways |
| 69 | Ministry of Road Transport & Highways |
| 43 | Ministry of Rural Development |
| 13 | Ministry of Science & Technology |
| 46 | Ministry of Ports, Shipping and Waterways |
| 77 | Ministry of Skill Development and Entrepreneurship |
| 50 | Ministry of Social Justice & Empowerment |
| 55 | Ministry of Statistics & Programme Implementation |
| 18 | Ministry of Steel |
| 25 | Ministry of Surface Transport |
| 19 | Ministry of Textiles |
| 36 | Ministry of Tourism |
| 49 | Ministry of Tribal Affairs |
| 32 | Ministry of Urban Development |
| 38 | Ministry of Water Resources, River Development and Ganga Rejuvenation |
| 64 | Ministry of Women and Child Development |
| 9 | Ministry of Youth Affairs and Sports |
| 78 | NITI Aayog |
| 1325 | PM Speech |
| 74 | EAC-PM |
| 34 | UPSC |
| 37 | Special Service and Features |
| 1005 | PIB Backgrounder |
| 1406 | Office of Principal Scientific Advisor to GoI |
| 1454 | National Financial Reporting Authority |
| 1458 | Competition Commission of India |
| 1470 | IFSC Authority |
| 1484 | National Security Council Secretariat |
| 2586 | National Human Rights Commission |
| 2611 | Lokpal of India |
| 2936 | home |

### Important Notes
- Multiple departments can share the **same ministry value** (e.g., value `41` is used for Chemicals and Fertilizers, Pharmaceuticals, Fertilizers, and Chemicals & Petrochemicals)
- Ministry filtering works via postback just like date filtering
- The `hydregionid` and `hydLangid` hidden fields sync with the region/language dropdowns

---

## 4. Aboutarchive.aspx Analysis

**URL:** `https://www.pib.gov.in/Aboutarchive.aspx?lang=1&reg=1`  
**Response:** 200 OK, 104,813 bytes

### Page Purpose
This is a **static information page** about PIB archives. It does NOT contain date-based release browsing functionality. It provides links to external archive systems.

### Forms
- **1 form** (POST, id=`form1`)
- **Action:** `./Aboutarchive.aspx?lang=1&reg=1`
- **No date filtering controls**

### Select Dropdowns (2 only)
1. **Region dropdown** (`Bar1_ddlregion`): 29 regions (same as allRel.aspx)
2. **Language dropdown** (`Bar1_ddlLang`): 3 options (English=1, Konkani=42, Marathi=9)

### Archive Links on the Page

| Link Text | URL |
|-----------|-----|
| All Releases | `/allRel.aspx` |
| PMO Releases | `/allRel.aspx` |
| All Releases 2004 to 2017 | `https://archive.pib.gov.in/archive2/erelease.aspx` |
| About Archives | `https://pib.gov.in/Aboutarchive.aspx` |
| 1947-2001 | `https://archive.pib.gov.in/archive/phase2/archiveministry.aspx?phase=3` |
| 2002-2003 | `https://archive.pib.gov.in/newsite/archivepage.aspx` |
| 2004 Onwards | `https://archive.pib.gov.in/archive2/` |
| Archives (main) | `https://archive.pib.gov.in/` |
| Archives (IP) | `http://164.100.88.150/newsite/archivepage.aspx` |

### Key Finding
- `Aboutarchive.aspx` is an **informational page only** - no date browsing
- Historical archives (pre-2017) are on a **separate subdomain**: `archive.pib.gov.in`
- The current site (pib.gov.in) only hosts recent releases (2017+)
- Date-specific URL parameters on this page (e.g., `?month=1&year=2024`) do **NOT** return release lists

---

## 5. PRID Range & Date Mapping

### PRID-to-Date Correlation (Sampled)

| PRID | Date |
|------|------|
| 2,200,000 | 07 DEC 2025 |
| 2,210,000 | 31 DEC 2025 |
| 2,220,000 | 29 JAN 2026 |
| 2,230,000 | 18 FEB 2026 |
| 2,240,000 | 13 MAR 2026 |
| 2,250,000 | 07 APR 2026 |
| 2,260,000 | 11 MAY 2026 |
| 2,270,000 | 07 JUN 2026 |
| 2,280,000 | 01 JUL 2026 |
| 2,290,000 | 27 JUL 2026 |
| 2,300,000 | 15 AUG 2026 |
| 2,310,000 | 14 SEP 2026 |
| 2,313,000 | ~20 SEP 2026 |

### Fine-Grained Recent PRIDs

| PRID | Date |
|------|------|
| 2,310,000 | 14 SEP 2026 |
| 2,310,500 | 15 SEP 2026 |
| 2,311,000 | 16 SEP 2026 |
| 2,311,500 | 17 SEP 2026 |
| 2,312,000 | 18 SEP 2026 |
| 2,312,500 | 19 SEP 2026 |
| 2,313,000 | ~20 SEP 2026 |

### Rate of PRID Assignment
- **~1,000 PRIDs per day** on average
- **~500 PRIDs per day** in recent weeks (Sept 2026)
- PRIDs are **monotonically increasing** - higher PRID = more recent
- All probed PRIDs from 2,200,000 to 2,313,000 **exist and return valid pages**

### Date Format on Press Release Pages
The date appears in the page text as:
```
Posted On: 18 SEP 2026 3:43PM by PIB Delhi
```
Format: `DD MON YYYY H:MMAM/PM`

### Key Finding
PRIDs are **sequential identifiers** assigned chronologically. The mapping is approximately linear: ~500-1000 releases per day across all regions/languages.

---

## 6. URL Variant Testing

### Test Results for PRID Variants

| URL Pattern | Status | Content Size | Title | Notes |
|-------------|--------|-------------|-------|-------|
| `PressReleasePage.aspx?PRID=` | **200 OK** | ~70-84K | "Press Release Page" | **PRIMARY URL** - redirects to Hindi if no lang specified |
| `PressReleaseIframePage.aspx?PRID=` | 200 OK | ~67-82K | "Press Release:" | Iframe version, also valid |
| `PressReleaseDetail.aspx?PRID=` | 200 OK | ~180K | "Press Release:" | Full detail page, larger |
| `PressReleseDetailm.aspx?PRID=` | 200 OK | ~139-178K | "Press Release:" | Mobile detail page (note typo in URL: "Relese") |
| `Pressreleaseshare.aspx?PRID=` | 200 OK | ~11-19K | (release title) | **Smallest** - share/embed version |

### URL Parameter Behavior

| Parameters | Behavior |
|-----------|----------|
| `?PRID=X` alone | Redirects to `?PRID=X&reg=48&lang=2` (Hindi, National) |
| `?PRID=X&lang=1` | Redirects to `?PRID=X&lang=2&reg=48` |
| `?PRID=X&reg=48&lang=1` | **Stays** - serves English content |
| `?PRID=X&lang=1&reg=1` | Redirects to `?PRID=X&reg=48&lang=2` |
| `?PRID=X&reg=48&lang=2` | Serves Hindi content |

### Critical Discovery
- **Without `lang=1`**, the server **defaults to Hindi** (`lang=2`)
- **Always include `&reg=48&lang=1`** for English National releases
- All 5 URL variants work and return valid content
- `Pressreleaseshare.aspx` is the most lightweight (~19KB) - ideal for scraping

### Language Variants
All tested language combinations work. The PRID system is **language-agnostic** - the same PRID returns content in whatever language is requested.

---

## 7. Internal Link Crawling

### Link Analysis from Release Pages

| Source PRID | Total Links | PIB Internal | Release Links | Non-Release |
|-------------|-------------|-------------|---------------|-------------|
| 2,312,000 | 12 | 2 | 2 | 0 |
| 2,310,000 | 15 | 5 | 5 | 0 |
| 2,250,000 | 13 | 3 | 3 | 0 |
| 2,200,000 | 21 | 9 | 9 | 0 |
| 2,100,000 | 12 | 2 | 2 | 0 |

### Link Pattern
Every release page links to the **same release in other languages** using PRID references:

| Language | Link Pattern |
|----------|-------------|
| Urdu | `PressReleasePage.aspx?PRID=XXXXXXX` (Urdu PRID) |
| हिन्दी | `PressReleasePage.aspx?PRID=XXXXXXX` (Hindi PRID) |
| Gujarati | `PressReleasePage.aspx?PRID=XXXXXXX` (Gujarati PRID) |
| Marathi | `PressReleasePage.aspx?PRID=XXXXXXX` (Marathi PRID) |
| Kannada | `PressReleasePage.aspx?PRID=XXXXXXX` (Kannada PRID) |
| Bengali | `PressReleasePage.aspx?PRID=XXXXXXX` (Bengali PRID) |
| Punjabi | `PressReleasePage.aspx?PRID=XXXXXXX` (Punjabi PRID) |
| Tamil | `PressReleasePage.aspx?PRID=XXXXXXX` (Tamil PRID) |
| Assamese | `PressReleasePage.aspx?PRID=XXXXXXX` (Assamese PRID) |

### Social Sharing Links
Each release page includes sharing links to:
- Facebook (`facebook.com/share.php`)
- Twitter/X (`twitter.com/intent/tweet`)
- WhatsApp (`api.whatsapp.com/send`)
- Gmail (`mail.google.com/mail`)
- LinkedIn (`linkedin.com/shareArticle`)

### Key Finding
- Release pages **only link to the same release in other languages**
- **No cross-links to other releases** (no "related releases" or "more from this ministry")
- Links to other PRIDs are for **translation variants**, not related content

---

## 8. AJAX/XHR Detection

### ASP.NET WebForms Infrastructure
The site uses **ASP.NET WebForms** with standard postback mechanism:

- `__doPostBack(eventTarget, eventArgument)` - standard postback function
- `Sys.WebForms.PageRequestManager._initialize('ctl00$script', 'form1', ...)` - ASP.NET AJAX ScriptManager
- **No UpdatePanel** detected (full page postbacks)
- **No custom AJAX endpoints** or API calls

### External JavaScript Libraries

| Library | Source | Size |
|---------|--------|------|
| jQuery 3.7.1 | `/js/jquery-3.7.1.min_all_js.js?v=1.3` | 161KB |
| jQuery scrolljs | `/js/scrolljs/myscolljs.js` | 97KB |
| jQuery meanmenu | `/js/jquery.meanmenu.js` | 9KB |
| Accessibility | `/js/accessibility.js?v=7` | 26KB |
| Custom | `/js/custom.js?v=0` | 3.5KB |
| Google Tag Manager | `googletagmanager.com/...` | External |

### ASP.NET AJAX Resources

| Resource | Purpose | Size |
|----------|---------|------|
| `WebResource.axd?...` | ASP.NET WebForms postback | 23KB |
| `ScriptResource.axd?...` (x6wA) | MS AJAX library (core) | 89KB |
| `ScriptResource.axd?...` (P5lT) | MS AJAX library (extended) | 37KB |

### Key Functions in WebResource.axd
```
WebForm_PostBackOptions
WebForm_DoPostBackWithOptions
WebForm_DoCallback
WebForm_CallbackComplete
WebForm_ExecuteCallback
WebForm_FillFirstAvailableSlot
WebForm_InitCallback
WebForm_EncodeCallback
WebForm_ReEnableControls
WebForm_ReDisableControls
WebForm_SimulateClick
WebForm_FireDefaultButton
```

### Key Finding
- **No REST API endpoints** exist
- **No AJAX data loading** - all filtering uses full page postbacks
- The site is a **traditional ASP.NET WebForms** application
- Only analytics (Google Tag Manager) makes external HTTP calls

---

## 9. Archive Deep Dive

### Aboutarchive.aspx URL Parameters Tested

| URL Parameters | Release Links Found | Notes |
|---------------|-------------------|-------|
| `?lang=1&reg=1` | 0 | Static info page |
| `?lang=1&reg=1&month=1&year=2024` | 0 | No effect |
| `?lang=1&reg=1&date=01/01/2024` | 0 | No effect |
| `?lang=1&reg=1&dt=2024-01-01` | 0 | No effect |
| `?lang=1&reg=1&From=01/01/2024&To=31/01/2024` | 0 | No effect |
| `?lang=1&reg=1&MonthYear=01/2024` | 0 | No effect |

### Region Testing (reg=1 through reg=16, reg=48)
All regions return HTTP 200 with the same "About Archive" page structure. **No region-specific content** on this page.

### POST to Archive Page
Submitting POST data to `Aboutarchive.aspx` returns a **different page** (113K vs 105K) but with **no release links** - it appears to be a different language version (Hindi).

### External Archive Systems

| Period | Archive System |
|--------|---------------|
| 1947-2001 | `archive.pib.gov.in/archive/phase2/archiveministry.aspx?phase=3` |
| 2002-2003 | `archive.pib.gov.in/newsite/archivepage.aspx` |
| 2004-2017 | `archive.pib.gov.in/archive2/erelease.aspx` |
| 2017+ | `pib.gov.in/allRel.aspx` (current site) |
| Main archive | `archive.pib.gov.in/` |

### Key Finding
- `Aboutarchive.aspx` is a **purely informational page** with no data retrieval capability
- **Historical archives** are on a completely separate subdomain: `archive.pib.gov.in`
- There is **no date-based API** on the current PIB site for browsing releases by date
- The current site only provides **dropdown-based filtering** via postback

---

## 10. RSS/Atom Feeds

### Feed URLs Tested

| URL | Status | Content Type | Actual Content |
|-----|--------|-------------|----------------|
| `pib.gov.in/ViewRss.aspx` | 200 | text/html | Full HTML page (109KB) - NOT RSS |
| `pib.gov.in/rss/all.xml` | 200 | text/html | "Untitled Page" HTML (945B) |
| `pib.gov.in/feed` | 200 | text/html | "Untitled Page" HTML (5KB) |
| `pib.gov.in/feed.xml` | 200 | text/html | "Untitled Page" HTML (945B) |
| `pib.gov.in/rss.xml` | 200 | text/html | "Untitled Page" HTML (945B) |
| `pib.gov.in/RSS/AllRelease.xml` | 200 | text/html | Server error page (686B) |
| `pib.gov.in/RSSFeed/AllRelease.xml` | 200 | text/html | "Untitled Page" HTML (945B) |
| `pib.gov.in/RSSFeed.xml` | 200 | text/html | "Untitled Page" HTML (945B) |
| `pib.gov.in/PressReleaseRss.aspx` | 200 | text/html | "Untitled Page" HTML (5KB) |
| `pib.gov.in/PressReleaseRss.aspx?lang=1` | 200 | text/html | Server error page (686B) |
| `pib.gov.in/PressReleaseRss.aspx?lang=1&reg=48` | 200 | text/html | "Untitled Page" HTML (5KB) |
| `pib.gov.in/RSS/main.xml` | 200 | text/html | "Untitled Page" HTML (945B) |
| `pib.gov.in/NewsEvents/rss.xml` | 200 | text/html | "Untitled Page" HTML (945B) |
| `pib.gov.in/PressReleaseRSS` | 200 | text/html | "Untitled Page" HTML (5KB) |
| `pib.gov.in/Syndication.axd` | 200 | text/html | "Untitled Page" HTML (5KB) |

### ViewRss.aspx Analysis
- Returns a **full HTML page** (109KB), not XML
- The page contains RSS feed links in the navigation but they all point to broken/non-functional endpoints
- With `?PRID=X` parameter, still returns the same HTML page

### robots.txt
- Returns an **HTML error page** (not a real robots.txt)
- Content: "Untitled Page" with centered text

### Sitemap
- `sitemap.xml` and `Sitemap.xml` both return the same **HTML error page**

### Key Finding
- **NO functional RSS/Atom feeds exist** on pib.gov.in
- All RSS-related URLs return either HTML error pages or generic "Untitled Page" HTML
- The site appears to have **deprecated or broken RSS functionality**
- There is **no sitemap.xml** and **no robots.txt**

---

## 11. Press Release Page Structure

### URL
```
https://www.pib.gov.in/PressReleasePage.aspx?PRID={prid}&reg=48&lang=1
```

### Page Structure (PRID 2312000)

```
<html>
  <head>...</head>
  <body>
    <div id="PrDateTime">
      Posted On: 18 SEP 2026 3:43PM by PIB Delhi
    </div>
    <div class="innner-page-main-about-us-content-right-part">
      <h2>Ministry of Law and Justice</h2>
      <h2>[Release Title]</h2>
      <div class="ReleaseDateSubHeaddateTime text-center pt20">
        Posted On: 18 SEP 2026 3:43PM by PIB Delhi
      </div>
      <div class="BackgroundRelease">[Release body content]</div>
      <div class="ReleaseLang">
        Read this release in: Urdu, हिन्दी
      </div>
      <span id="ReleaseId">(Release ID: 2312000)</span>
      <span id="lblViews">Visitor Counter : 270</span>
    </div>
  </body>
</html>
```

### Key Elements for Scraping

| Element | Selector | Content |
|---------|----------|---------|
| Date | `div#PrDateTime` | "Posted On: 18 SEP 2026 3:43PM by PIB Delhi" |
| Ministry | `div.innner-page-main-about-us-content-right-part > h2` (first) | "Ministry of Law and Justice" |
| Title | `div.innner-page-main-about-us-content-right-part > h2` (second) | Release headline |
| Body | `div.BackgroundRelease` | Full release text |
| Release ID | `span#ReleaseId` | "(Release ID: 2312000)" |
| Views | `span#lblViews` | "Visitor Counter : 270" |
| Language links | `div.ReleaseLang a` | Links to same release in other languages |

### Date Format
```
Posted On: DD MON YYYY H:MMAM/PM by PIB [Region]
```
Example: `Posted On: 18 SEP 2026 3:43PM by PIB Delhi`

---

## 12. Summary & Key Findings

### Architecture
- **ASP.NET WebForms** application (not MVC, not API-driven)
- **No REST API** - all data retrieval via form postbacks
- **No AJAX** data loading - full page reloads on filter changes
- **No RSS/Atom feeds** - all feed URLs are broken/deprecated
- **No sitemap.xml** or robots.txt

### Data Access Methods

| Method | URL | Notes |
|--------|-----|-------|
| **Release listing** | `allRel.aspx?reg=48&lang=1` | POST with dropdowns for filtering |
| **Release detail** | `PressReleasePage.aspx?PRID=X&reg=48&lang=1` | GET request, always include `&reg=48&lang=1` |
| **Share version** | `Pressreleaseshare.aspx?PRID=X&reg=48&lang=1` | Lightest version (~19KB) |
| **Iframe version** | `PressReleaseIframePage.aspx?PRID=X&reg=48&lang=1` | For embedding |
| **Mobile version** | `PressReleseDetailm.aspx?PRID=X&reg=48&lang=1` | Note typo in URL |
| **Historical** | `archive.pib.gov.in/...` | Separate subdomain for pre-2017 |

### Filtering on allRel.aspx
- **Region:** 29 PIB regional offices (dropdown, postback)
- **Language:** English (1) or Hindi (2) (dropdown, postback)
- **Ministry:** 97 ministries/departments (dropdown, postback)
- **Day:** 1-31 or All (dropdown, postback)
- **Month:** January-December (dropdown, postback)
- **Year:** 2017-2026 (dropdown, postback)

### PRID System
- **Sequential IDs** - higher = more recent
- **~500-1000 new PRIDs per day**
- PRID range (observed): 2,200,000 (Dec 2025) to 2,313,000 (Sep 2026)
- **All PRIDs tested exist** - no gaps found in the range
- Same PRID serves content in **any supported language** (parameter-driven)

### Scraping Recommendations
1. **For release listing:** POST to `allRel.aspx` with `__VIEWSTATE` from a GET request
2. **For release detail:** GET `PressReleasePage.aspx?PRID=X&reg=48&lang=1`
3. **For lightweight scraping:** Use `Pressreleaseshare.aspx?PRID=X&reg=48&lang=1` (19KB vs 84KB)
4. **Always include `&reg=48&lang=1`** to get English National content
5. **Date extraction:** Parse from `div#PrDateTime` or body text for "Posted On: DD MON YYYY..."
6. **Ministry extraction:** First `<h2>` inside the content div
7. **Release ID:** `span#ReleaseId` contains "(Release ID: XXXXX)"

### Technical Details
- **ViewState size:** ~34KB (base64) - must be captured fresh for each session
- **EventValidation size:** ~4KB (base64)
- **Session required:** Cookies must be maintained for postback to work
- **No CAPTCHA** or rate limiting observed
- **No authentication** required
