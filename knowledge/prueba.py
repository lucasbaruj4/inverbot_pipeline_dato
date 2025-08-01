import requests
import os

response = requests.post(
    "https://api.firecrawl.dev/v1/crawl",
    headers={"Authorization":"Bearer: API"},
    json={"url":"https://en.wikipedia.org/wiki/OpenAI",
          "maxDepth":3,
          "scrapeOptions": {
              "formats":["json"],
              "jsonOptions":{
                  "schema":{
                    "title":"test JSON Schema for firecrawl learning",
                    "description":"it's just crawling stuff from wikipedia to learn about the API response formats",
                    "type":"object",
                    "properties": {
                        "name": {
                            "description": "the name of tha page you're currently crawling",
                            "type": "string"
                        },
                        "theme":{
                            "description":"the theme or themes you're extracting from the page",
                            "type": "string"
                        },
                        "entertainment": {
                            "description": "If you had to give a rating from 1-10, calificating subjectively how entertaining the content you're scraping is, give a number in that range",
                            "type":"number",
                            "exclusiveMinimum": 0
                        }
                    },
                    "required":["name", "theme", "entertainment"]
                  },
                  "systemPrompt":"You're a world renowned expert on Scraping pages and giving entertainment qualifications, you love what you do and you're great at it, you excel in taking with pieces of data from a messy page and turning it into the expected JSON format",
                  "prompt":"Scrape the page and based on the scraped content put that data into the assigned JSON format"
              },
          }
          
    }  
    
)
data = response.json()
id = data.get("id",{})

