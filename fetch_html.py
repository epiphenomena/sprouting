import requests

def fetch_html(url):
    """
    Fetches the HTML content of a given URL.

    Parameters:
    url (str): The URL to fetch.

    Returns:
    str: The HTML content of the page, or an error message if fetching fails.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        return f"Error fetching HTML: {str(e)}"