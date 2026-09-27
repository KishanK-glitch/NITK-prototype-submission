import requests
from bs4 import BeautifulSoup

def fetch_live_scheme_data(scheme_name: str) -> str:
    """
    Fetches live data for a government scheme.
    Keeps latency under 3 seconds to avoid Twilio webhook timeouts.
    """
    if not scheme_name:
        return "No specific scheme requested."

    urls = {
        "pm_kisan": "https://pmkisan.gov.in/",
        "pmjdy": "https://pmjdy.gov.in/scheme",
        "atal_pension": "https://www.npscra.nsdl.co.in/scheme-details.php",
        "pm_svanidhi": "https://pmsvanidhi.mohua.gov.in/",
        "pm_vishwakarma": "https://pmvishwakarma.gov.in/",
    }

    norm_name = scheme_name.lower().strip().replace(" ", "_")
    url = urls.get(norm_name, "https://www.myscheme.gov.in/")

    try:
        response = requests.get(url, timeout=3, verify=False)
        if response.status_code != 200:
            return f"Official portal returned HTTP status {response.status_code}."

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.extract()

        raw_text = soup.get_text(separator=" ", strip=True)
        # Limit to 1500 chars to avoid breaching Groq TPM limits
        cleaned = " ".join(raw_text.split())[:1500]
        return f"LIVE SOURCE: {url}\n{cleaned}"

    except requests.exceptions.RequestException as e:
        print(f"[Crawler Exception]: {e}")
        return f"Government portal at {url} timed out or is temporarily unreachable."