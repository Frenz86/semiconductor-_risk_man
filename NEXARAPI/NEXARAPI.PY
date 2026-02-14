import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv(override=True)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TOKEN_URL = "https://identity.nexar.com/connect/token"
API_URL = "https://api.nexar.com/graphql"

def get_detailed_part_info(mpn: str):
    with httpx.Client() as client:
        # 1. Auth
        token_data = {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": "supply.domain"
        }
        auth_res = client.post(TOKEN_URL, data=token_data)
        token = auth_res.json().get("access_token")

        # 2. Query (Include seller details for Taiwan verification)
        query = """
        query Search($mpn: String!) {
          supSearchMpn(q: $mpn) {
            results {
              part {
                mpn
                manufacturer { name }
                shortDescription
                sellers {
                  company {
                    name
                    id
                  }
                  offers {
                    inventoryLevel
                    moq
                    prices {
                      quantity
                      convertedPrice
                      convertedCurrency
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"query": query, "variables": {"mpn": mpn}}
        
        response = client.post(API_URL, json=payload, headers=headers)
        return response.json()

if __name__ == "__main__":
    response_json = get_detailed_part_info("CC0603KRX7R9BB104")
    
    # --- DEBUGGING CHECK ---
    if "errors" in response_json:
        print("!!! GRAPHQL ERROR DETECTED !!!")
        print(json.dumps(response_json["errors"], indent=2))
    elif "data" not in response_json:
        print("!!! UNEXPECTED RESPONSE FORMAT !!!")
        print(response_json)
    else:
        # --- PROCESSING DATA ---
        results = response_json['data']['supSearchMpn']['results']
        if not results:
            print("No parts found.")
        else:
            for result in results:
                part = result['part']
                print(f"--- {part['mpn']} by {part['manufacturer']['name']} ---")
                print(f"Description: {part.get('shortDescription', 'N/A')}")

                # Show all sellers with details
                sellers = part.get('sellers', [])
                print(f"\n=== SELLERS ({len(sellers)}) ===")

                for seller in sellers:
                    company = seller.get('company', {})
                    company_name = company.get('name', 'Unknown')
                    company_id = company.get('id', 'N/A')
                    print(f"\n• {company_name} (ID: {company_id})")

                    for offer in seller.get('offers', []):
                        inv = offer.get('inventoryLevel')
                        moq = offer.get('moq')
                        prices = offer.get('prices', [])

                        if inv:
                            print(f"  Stock: {inv:,} units")
                        if moq:
                            print(f"  MOQ: {moq}")
                        if prices:
                            for price in prices[:3]:  # Show first 3 price breaks
                                qty = price['quantity']
                                print(f"  {qty:,} units: {price.get('convertedCurrency', '')} {price.get('convertedPrice', '')}")

                # Calculate total inventory
                inventory_list = []
                for seller in sellers:
                    for offer in seller.get('offers', []):
                        inv = offer.get('inventoryLevel')
                        if inv: inventory_list.append(inv)

                print(f"\n>>> Total Market Stock: {sum(inventory_list):,} units")
                print("=" * 50)