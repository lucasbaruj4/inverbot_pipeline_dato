from prueba import id
import requests
scrape_response = requests.get(
    f"https://api.firecrawl.dev/v1/crawl/86c2d536-1487-4475-88cb-6cca8c53c096",
    headers={"Authorization":"Bearer: fc-ff1c3ee38f5043cebe7940744657ff3e"}
)

respuesta = scrape_response.json()
datos = respuesta.get("data", {})
json = datos[0]["json"]
print(json)