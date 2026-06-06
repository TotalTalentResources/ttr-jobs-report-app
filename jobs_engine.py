from fredapi import Fred
from openai import OpenAI
import time
import requests
import os

# ✅ Helper function (retry logic)
def fetch_series(fred, series_id):
    for attempt in range(3):
        try:
            return fred.get_series(series_id)
        except Exception as e:
            print(f"Retrying {series_id}... attempt {attempt+1}")
            time.sleep(2)
    return None
def fetch_bls_latest(series_id):
    url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

    headers = {"Content-type": "application/json"}

    data = {
        "seriesid": [series_id],
        "latest": "true"
    }

    response = requests.post(url, json=data, headers=headers)
    json_data = response.json()

    try:
        latest = json_data["Results"]["series"][0]["data"][0]
        value = float(latest["value"])
        date = f"{latest['year']}-{latest['period']}"

        return value, date

    except:
        return None, None


# ✅ Main function
def generate_report(industry,expected_jobs_k):

    fred = Fred(api_key=os.getenv("FRED_API_KEY"))
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # 📊 Pull data (with retry)
    payrolls = fetch_series(fred, "PAYEMS")
    
    payroll_changes = payrolls.diff()
    current_change = payroll_changes.iloc[-1]
   
   
    unemployment = fetch_series(fred, "UNRATE")
    # BLS for real-time (Latest Release)
    payroll_current, payroll_date = fetch_bls_latest("CES0000000001")
    unemployment_current, unemp_date = fetch_bls_latest("LNS14000000")

        # ✅ Fallback if BLS fails
    if payroll_current is None:
        payroll_current = payrolls.iloc[-1]

    if unemployment_current is None:
        unemployment_current = unemployment.iloc[-1]


    #Continue using FRED for everything else
    participation = fetch_series(fred, "CIVPART")
    wages = fetch_series(fred, "AHETPI")

    manufacturing = fetch_series(fred, "MANEMP")
    transportation = fetch_series(fred, "CES4300000001")
    warehousing = fetch_series(fred, "CEU4348400001")

    # ✅ Safety check
    if any(x is None for x in [payrolls, unemployment, participation, wages,
                               manufacturing, transportation, warehousing]):
        return "⚠️ Error: Unable to retrieve jobs data right now. Please try again."

    # ✅ Core data
    data = {
    # ✅ REAL-TIME from BLS
    "payroll_current": payroll_current,
    "unemployment_current": unemployment_current,

    # ✅ HISTORY from FRED
    "payroll_previous": payrolls.iloc[-2],
    "unemployment_previous": unemployment.iloc[-1],

    # Other indicators
    "participation": participation.iloc[-1],
    "wages": wages.iloc[-1],
}


    data["payroll_change"] = data["payroll_current"] - data["payroll_previous"]
    data["unemployment_change"] = data["unemployment_current"] - data["unemployment_previous"]
    
    # ✅ Headline jobs from monthly change
    
    data["headline_jobs_k"] = int(round(current_change))

    # ✅ Compare vs expectations
    data["jobs_surprise"] = data["headline_jobs_k"] - expected_jobs_k

    if data["jobs_surprise"] > 20:
        data["jobs_vs_expectation"] = "above expectations"
    elif data["jobs_surprise"] < -20:
        data["jobs_vs_expectation"] = "below expectations"
    else:
        data["jobs_vs_expectation"] = "in line with expectations"
    
    # ✅ Safety check: prevent bad headline values
    if data["headline_jobs_k"] < 50 or data["headline_jobs_k"] > 500:
        return "⚠️ Jobs report data is still updating. Please try again in a few minutes."
    
   
    data["unemployment_rate"] = round(data["unemployment_current"], 1)
    data["manufacturing"] = manufacturing.iloc[-1]
    data["manufacturing_prev"] = manufacturing.iloc[-2]

    data["transportation"] = transportation.iloc[-1]
    data["transportation_prev"] = transportation.iloc[-2]

    data["warehousing"] = warehousing.iloc[-1]
    data["warehousing_prev"] = warehousing.iloc[-2]
    data["manufacturing_change"] = data["manufacturing"] - data["manufacturing_prev"]
    data["transportation_change"] = data["transportation"] - data["transportation_prev"]
    data["warehousing_change"] = data["warehousing"] - data["warehousing_prev"]


    sector_data = {
        "manufacturing_current": manufacturing.iloc[-1],
        "manufacturing_change": manufacturing.iloc[-1] - manufacturing.iloc[-2],
        "transportation_current": transportation.iloc[-1],
        "transportation_change": transportation.iloc[-1] - transportation.iloc[-2],
        "warehousing_current": warehousing.iloc[-1],
        "warehousing_change": warehousing.iloc[-1] - warehousing.iloc[-2],
    }

    

    sector_diff = sector_data["transportation_change"] - sector_data["manufacturing_change"]

    # 📈 Trends
    manufacturing_trend = manufacturing.iloc[-4:].diff().mean()
    transportation_trend = transportation.iloc[-4:].diff().mean()
    warehousing_trend = warehousing.iloc[-4:].diff().mean()

    # 🧠 Structured data
    structured_data = f"""
Nonfarm Payrolls: {data['payroll_current']} (Change: {data['payroll_change']})
Unemployment Rate: {data['unemployment_current']}% (Change: {data['unemployment_change']}%)
Labor Force Participation: {data['participation']}%
Average Hourly Earnings Index: {data['wages']}

Sector Breakdown:
- Manufacturing: {sector_data['manufacturing_current']} (Change: {sector_data['manufacturing_change']})
- Transportation & Warehousing: {sector_data['transportation_current']} (Change: {sector_data['transportation_change']})
- Warehousing: {sector_data['warehousing_current']} (Change: {sector_data['warehousing_change']})

3-Month Avg Job Growth:
- Manufacturing: {manufacturing_trend}
- Transportation & Warehousing: {transportation_trend}
- Warehousing: {warehousing_trend}

Relative Momentum:
Transportation minus Manufacturing job growth: {sector_diff}
"""

    # ✅ Industry-specific context
    if industry == "Distribution":
        industry_context = """
Focus on distribution companies:
- Warehouse labor availability
- Throughput and fulfillment demand
- Inventory movement and restocking signals
"""

    elif industry == "Manufacturing":
        industry_context = """
Focus on manufacturing companies:
- Production demand and factory hiring
- Output trends and capacity utilization
"""

    elif industry == "Logistics":
        industry_context = """
Focus on logistics providers:
- Freight demand and transportation activity
- Warehouse throughput and labor constraints
"""

    else:
        industry_context = ""

    # 🤖 GPT call
    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {
                "role": "system",
                "content": "You are a senior economist advising business leaders."
            },
            {
                "role": "user",
                "content": f"""


Write a concise, client-ready email summarizing the latest U.S. jobs report.

Audience:
Executives in {industry} organizations.

Perspective:
All analysis must be framed from the perspective of a {industry} operator.
Interpret ALL data through how it impacts THEIR business, not the overall economy.

{industry_context}

IMPORTANT:
- Do NOT just summarize data — interpret it
- Lead with the key takeaway immediately
- Be concise, high signal, and decision-oriented
- Use clear, confident language (no hedging)
- The first sentence MUST include jobs added, whether the report was above/below expectations (with the expected number), and the unemployment rate, without repeating wording from the subject line
- Keep the first sentence under 25 words and make it sharp and direct
- Do NOT include section labels (e.g., "Executive summary", "Sector breakdown") in the output; write as a continuous, natural email
- Write in 3–4 short paragraphs with a natural flow, not as a structured report
- Write like a natural email from a senior advisor, not a formatted report


REQUIREMENTS:

1. HEADLINE FACTS (MANDATORY):
- Clearly state jobs added using the headline value provided
- State whether jobs came in above, below, or in line with expectations, and explicitly use the provided expected_jobs_k value (do not substitute or infer another estimate)
- Use phrasing "above expectations of ~XK" or "below expectations of ~XK" (do not use "estimate")
- Clearly state the unemployment rate

2. EXECUTIVE SUMMARY:
- 2–3 sentences describing whether conditions are strengthening, stable, or softening
- Describe any notable change in hiring composition or sector trends without comparing to prior headline job growth


3. SECTOR BREAKDOWN:
- Manufacturing: state whether hiring increased or decreased and what it implies for production
- Transportation / Distribution: explain demand for freight and movement of goods
- Warehousing: explain implications for inventory levels and fulfillment activity


4. INDUSTRY-SPECIFIC IMPACT:
- Tailor specifically to {industry}
- Be explicit and concrete — reference operational realities specific to this industry (e.g., warehouses, fleet capacity, plant staffing, etc.).
- Explain implications for:
  → hiring difficulty
  → labor availability
  → wage pressure
  → demand outlook


5. ACTIONABLE RECOMMENDATIONS:
- Provide 3–4 specific, decisive recommendations executives should act on now (hiring, pricing, capacity planning, or workforce strategy)

6. BOTTOM LINE:
- One sharp, decisive takeaway sentence (no more than 15 words)

7. CALL TO ACTION
- Add a brief, natural closing sentence offering to discuss implications with the client
- Keep it professional and low-pressure (not salesy)
- Do not repeat the bottom line


OUTPUT FORMAT:

Subject: [Include jobs added + implication, e.g., "Jobs Growth Remains Solid at ~XXXK — Labor Conditions Tighten"]

Hi [Client],

[Executive summary]

[Sector breakdown paragraph]

[Industry-specific paragraph]

[Actionable recommendations]

Bottom Line:
[One sentence takeaway]

[One short call-to action sentence]

DATA INSTRUCTIONS (CRITICAL):
- Use the "Jobs added" value as the official headline number
- Use payroll_change only for deeper context if needed
- Do NOT confuse the two


DATA:
- Jobs added (headline): {data["headline_jobs_k"]}K
- Jobs vs expectations: {data['jobs_vs_expectation']}
- Expected jobs: {expected_jobs_k}K
- Unemployment rate: {data["unemployment_rate"]}%

- Payroll change (revised context): {data["payroll_change"]}

- Manufacturing change: {data["manufacturing_change"]}
- Transportation change: {data["transportation_change"]}
- Warehousing change: {data["warehousing_change"]}

STYLE:
- Professional, confident, and direct
- Client-facing (not academic)
- Clear and concise
- No bullet points
- No filler words
- The closing call to action should sound consultative and relationship-focused
"""
            }
        ]
    )

    return response.choices[0].message.content
