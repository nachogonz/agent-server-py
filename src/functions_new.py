import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union

import httpx

logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3001")
REQUEST_TIMEOUT = 10.0


# Helper function for HTTP requests with timeout
async def fetch_with_timeout(url: str, method: str = "GET", json_data: Dict = None, timeout: float = REQUEST_TIMEOUT) -> httpx.Response:
    """Make HTTP request with timeout."""
    async with httpx.AsyncClient() as client:
        if method.upper() == "GET":
            response = await client.get(url, timeout=timeout)
        elif method.upper() == "POST":
            response = await client.post(url, json=json_data, timeout=timeout)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        return response


class FunctionContext:
    """Function context containing all available functions for the agent."""

    def create_function_context(self) -> List[Dict[str, Any]]:
        """Create function definitions for the OpenAI LLM."""
        return [
            {
                "name": "checkClientId",
                "description": "Check if a client ID exists in the database and greet the user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "clientId": {
                            "type": "string",
                            "description": "The client ID to check"
                        }
                    },
                    "required": ["clientId"]
                }
            },
            {
                "name": "searchProducts", 
                "description": "Search for products in the database using vector similarity for better precision",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for products - be specific about what you are looking for"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "createOrder",
                "description": "Create a new order for a client with products and quantities",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "clientId": {
                            "type": "string",
                            "description": "The client ID for the order"
                        },
                        "products": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "productId": {
                                        "type": "string",
                                        "description": "The product ID to order"
                                    },
                                    "quantity": {
                                        "type": "number",
                                        "description": "The quantity of this product to order"
                                    }
                                },
                                "required": ["productId", "quantity"]
                            },
                            "description": "Array of products with their quantities"
                        }
                    },
                    "required": ["clientId", "products"]
                }
            },
            # Add more functions as needed for different agent modes
        ]

    # ===================== ORDER FUNCTIONS =====================

    async def check_client_id(self, clientId: str) -> str:
        """Check if a client ID exists in the database."""
        try:
            logger.info(f"=======> checking client ID: {clientId}")
            response = await fetch_with_timeout(f"{API_BASE_URL}/users/search/{clientId}")

            if response.status_code == 404:
                return f"Client ID {clientId} not found. Please provide a valid client ID."
            elif response.status_code != 200:
                raise Exception(f"Failed to check client ID, status code: {response.status_code}")

            user_data = response.json()
            return f"Welcome back, {user_data['username']}! Your client ID {clientId} is valid. How can I help you today?"

        except Exception as error:
            return f"Error checking client ID '{clientId}': {error}"

    async def search_products(self, query: str) -> str:
        """Search for products using vector similarity."""
        try:
            logger.info(f"=======> searching products with query: '{query}'")

            response = await fetch_with_timeout(
                f"{API_BASE_URL}/products/search",
                method="POST",
                json_data={"query": query.strip()}
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"=======> search failed with status {response.status_code}: {error_text}")
                raise Exception(f"Failed to search products, status code: {response.status_code}: {error_text}")

            products = response.json()
            logger.info(f"=======> found {len(products) if products else 0} products")

            if not products:
                return f"No products found matching '{query}'. Please try again with different keywords."

            product_list = []
            for i, product in enumerate(products):
                score = f" (Relevance: {product.get('relevanceScore', 0) * 100:.1f}%)" if product.get('relevanceScore') else ""
                product_list.append(f"{i + 1}. {product['name']} - ${product['price']} (ID: {product['_id']}){score}")

            return f"Here are the products I found using vector similarity + text search for '{query}':\n\n" + "\n".join(product_list) + "\n\nPlease select a product by saying its number or name."

        except Exception as error:
            logger.error(f"=======> searchProducts error: {error}")
            return f"Error searching products: {error}. Please try again or contact support if the problem persists."

    async def create_order(self, clientId: str, products: List[Dict[str, Union[str, int]]]) -> str:
        """Create an order with multiple products."""
        try:
            logger.info(f"=======> creating order for client {clientId} with {len(products)} products")
            
            response = await fetch_with_timeout(
                f"{API_BASE_URL}/orders",
                method="POST",
                json_data={
                    "clientId": int(clientId),
                    "products": products
                }
            )

            if response.status_code != 200:
                raise Exception(f"Failed to create order, status code: {response.status_code}")

            order_data = response.json()
            product_summary = ", ".join([f"{p['quantity']}x product ID {p['productId']}" for p in products])
            return f"Order created successfully! Order ID: {order_data['_id']} with {product_summary}. Would you like me to finish the order now?"

        except Exception as error:
            return f"Error creating order: {error}"

    # Add all other function implementations here...
    # For brevity, I'm including just the core order functions
    # You can add the rest of the functions from the original file

    async def handle_function_call(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Handle function calls from the LLM."""
        try:
            if function_name == "checkClientId":
                return await self.check_client_id(arguments["clientId"])
            elif function_name == "searchProducts":
                return await self.search_products(arguments["query"])
            elif function_name == "createOrder":
                return await self.create_order(arguments["clientId"], arguments["products"])
            # Add more function handlers as needed
            else:
                return f"Function {function_name} not implemented."
        except Exception as error:
            logger.error(f"Error handling function call {function_name}: {error}")
            return f"Error executing {function_name}: {error}"