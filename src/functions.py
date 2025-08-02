import os
import asyncio
import logging
import json
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
        functions = []
        
        # Order Management Functions
        functions.extend([
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
            {
                "name": "createSingleProductOrder",
                "description": "Create a new order for a client with a single product and quantity (convenience function)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "clientId": {
                            "type": "string",
                            "description": "The client ID for the order"
                        },
                        "productId": {
                            "type": "string",
                            "description": "The product ID to order"
                        },
                        "quantity": {
                            "type": "number",
                            "description": "The quantity of this product to order"
                        }
                    },
                    "required": ["clientId", "productId", "quantity"]
                }
            },
            {
                "name": "finishOrder",
                "description": "Finish an order by providing delivery date and address",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "orderId": {
                            "type": "string",
                            "description": "The order ID to finish"
                        },
                        "date": {
                            "type": "string",
                            "description": "The delivery date"
                        },
                        "address": {
                            "type": "string",
                            "description": "The delivery address"
                        }
                    },
                    "required": ["orderId", "date", "address"]
                }
            },
            {
                "name": "getOrdersByClientId",
                "description": "Get all orders for a specific client ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "clientId": {
                            "type": "string",
                            "description": "The client ID to get orders for"
                        }
                    },
                    "required": ["clientId"]
                }
            }
        ])
        
        # Appointment Functions
        functions.extend([
            {
                "name": "createAppointment",
                "description": "Create a new dental appointment with patient information, appointment type, and timing",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patientName": {
                            "type": "string",
                            "description": "The full name of the patient"
                        },
                        "isReturningPatient": {
                            "type": "boolean",
                            "description": "Whether the patient has visited before (true) or is a new patient (false)"
                        },
                        "appointmentType": {
                            "type": "string",
                            "enum": ["Regular Checkup", "Cleaning", "Checkup and Cleaning", "Emergency", "Consultation", "Follow-up"],
                            "description": "The type of dental appointment"
                        },
                        "appointmentTime": {
                            "type": "string",
                            "description": "The confirmed appointment date and time in format 'Day Month Date Year at Time' (e.g., 'Tuesday January 15 2025 at 11:15 AM')"
                        },
                        "reminderPreference": {
                            "type": "string",
                            "enum": ["call", "text", "none"],
                            "description": "How the patient wants to be reminded about the appointment"
                        }
                    },
                    "required": ["patientName", "isReturningPatient", "appointmentType", "appointmentTime", "reminderPreference"]
                }
            },
            {
                "name": "checkAppointmentAvailability",
                "description": "Check appointment availability for a specific date and optionally specific time slots",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "The date to check availability for (e.g., 'Tuesday January 15 2025' or 'January 15 2025')"
                        },
                        "timeSlots": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional specific time slots to check (e.g., ['10:30 AM', '11:15 AM']). If not provided, will return all available slots."
                        }
                    },
                    "required": ["date"]
                }
            }
        ])
        
        # Lead Capture Functions
        functions.extend([
            {
                "name": "captureLead",
                "description": "Capture health insurance lead information from the sales call",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "call_outcome": {
                            "type": "string",
                            "enum": ["completed", "voicemail", "reschedule", "declined"],
                            "description": "The outcome of the sales call"
                        },
                        "coverage_type": {
                            "type": "string",
                            "enum": ["employer", "marketplace", "private", "uninsured"],
                            "description": "How the prospect currently gets health coverage"
                        },
                        "premium_change": {
                            "type": "string",
                            "enum": ["going_up", "staying_same", "dropping"],
                            "description": "How their premiums have been changing"
                        },
                        "zip_code": {
                            "type": "string",
                            "description": "The prospect's ZIP code"
                        },
                        "age": {
                            "type": "number",
                            "description": "The prospect's age"
                        },
                        "tobacco_user": {
                            "type": "boolean",
                            "description": "Whether the prospect uses tobacco"
                        },
                        "objection_text": {
                            "type": "string",
                            "description": "Exact wording of any concerns or objections raised"
                        },
                        "first_name": {
                            "type": "string",
                            "description": "The prospect's first name"
                        },
                        "last_name": {
                            "type": "string",
                            "description": "The prospect's last name"
                        },
                        "phone": {
                            "type": "string",
                            "description": "The prospect's phone number"
                        }
                    },
                    "required": ["call_outcome"]
                }
            }
        ])
        
        # Airline Functions
        functions.extend([
            {
                "name": "changeBooking",
                "description": "Change an existing flight booking (modify date, flight number, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "bookingCode": {
                            "type": "string",
                            "description": "The booking code/confirmation number for the reservation"
                        },
                        "newDate": {
                            "type": "string",
                            "description": "New flight date in YYYY-MM-DD format"
                        },
                        "newFlightNumber": {
                            "type": "string",
                            "description": "New flight number (e.g., AA1003)"
                        }
                    },
                    "required": ["bookingCode"]
                }
            },
            {
                "name": "checkInPassenger",
                "description": "Check in a passenger for their flight and assign seats. Can use either booking code or loyalty number.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "bookingCode": {
                            "type": "string",
                            "description": "The booking code/confirmation number for the reservation"
                        },
                        "loyaltyNumber": {
                            "type": "string",
                            "description": "The Aerolíneas Plus loyalty number"
                        },
                        "seatPreference": {
                            "type": "string",
                            "description": "Preferred seat number (e.g., 18C, 25A, 30F)"
                        }
                    }
                }
            },
            {
                "name": "reportLostBaggage",
                "description": "Report lost or missing baggage and create a tracking report",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "baggageCode": {
                            "type": "string",
                            "description": "The baggage claim number or tag code"
                        },
                        "passengerName": {
                            "type": "string",
                            "description": "Full name of the passenger who owns the baggage"
                        },
                        "lastSeenLocation": {
                            "type": "string",
                            "description": "Where the baggage was last seen (e.g., security checkpoint, baggage claim)"
                        }
                    },
                    "required": ["baggageCode", "passengerName", "lastSeenLocation"]
                }
            }
        ])
        
        # Consultation Functions
        functions.extend([
            {
                "name": "scheduleConsultation",
                "description": "Schedule an AI consultation with a potential client and create a calendar event",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_name": {
                            "type": "string",
                            "description": "Full name of the potential client"
                        },
                        "contact_method": {
                            "type": "string",
                            "description": "Email address or phone number to reach the client"
                        },
                        "project_description": {
                            "type": "string",
                            "description": "Detailed description of their AI project needs and requirements"
                        },
                        "consultation_outcome": {
                            "type": "string",
                            "enum": ["scheduled", "interested", "not_ready", "declined"],
                            "description": "The outcome of the consultation request"
                        },
                        "industry": {
                            "type": "string",
                            "description": "Their business industry or sector"
                        },
                        "business_challenges": {
                            "type": "string",
                            "description": "Specific problems they want AI to solve"
                        },
                        "timeline": {
                            "type": "string",
                            "description": "When they want to start the project"
                        },
                        "budget_range": {
                            "type": "string",
                            "description": "Their estimated budget range"
                        },
                        "preferred_date": {
                            "type": "string",
                            "description": "Preferred consultation date"
                        },
                        "preferred_time": {
                            "type": "string",
                            "description": "Preferred consultation time"
                        }
                    },
                    "required": ["client_name", "contact_method", "project_description", "consultation_outcome"]
                }
            },
            {
                "name": "checkCalendarAvailability",
                "description": "Check calendar for exact start time conflicts. Prevents double-booking by validating the specific time slot. Requires user location for accurate timezone.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "The date to check availability for (e.g., '2024-01-15')"
                        },
                        "startTime": {
                            "type": "string",
                            "description": "Starting time to check for conflicts (e.g., '2:00 PM', '14:00', '2 PM'). REQUIRED to prevent exact start time conflicts."
                        },
                        "location": {
                            "type": "string",
                            "description": "User location (city, state/country or timezone) to determine correct timezone (e.g., 'New York, NY', 'Los Angeles, CA', 'America/New_York')"
                        }
                    },
                    "required": ["date", "startTime", "location"]
                }
            }
        ])
        
        return functions

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

    async def create_single_product_order(self, clientId: str, productId: str, quantity: int) -> str:
        """Create an order with a single product (convenience function)."""
        try:
            # Default to 1 if quantity is not provided or is invalid
            order_quantity = quantity if quantity and quantity > 0 else 1
            return await self.create_order(clientId, [{"productId": productId, "quantity": order_quantity}])
        except Exception as error:
            return f"Error creating single product order: {error}"

    async def finish_order(self, orderId: str, date: str, address: str) -> str:
        """Finish an order by providing delivery date and address."""
        try:
            logger.info(f"=======> finishing order {orderId}")
            response = await fetch_with_timeout(
                f"{API_BASE_URL}/orders/finish/{orderId}",
                method="POST",
                json_data={
                    "date": date,
                    "address": address
                }
            )

            if response.status_code == 404:
                return f"Order {orderId} not found. Please check the order ID."
            elif response.status_code != 200:
                raise Exception(f"Failed to finish order, status code: {response.status_code}")

            order_data = response.json()
            return f"Order {orderId} has been successfully finished! Your order will be delivered to {address} on {date}. Thank you for your purchase!"

        except Exception as error:
            return f"Error finishing order: {error}"

    async def get_orders_by_client_id(self, clientId: str) -> str:
        """Get all orders for a specific client ID."""
        try:
            logger.info(f"=======> getting orders for client {clientId}")
            response = await fetch_with_timeout(f"{API_BASE_URL}/orders/user/{clientId}")

            if response.status_code != 200:
                raise Exception(f"Failed to get orders, status code: {response.status_code}")

            orders = response.json()

            if not orders:
                return f"No orders found for client ID {clientId}."

            order_list = []
            for i, order in enumerate(orders):
                status = order.get('status', 'Active')
                product_id = order.get('productId', 'N/A')
                order_list.append(f"{i + 1}. Order ID: {order['_id']} - Product: {product_id} - Status: {status}")

            return f"Here are your orders:\n" + "\n".join(order_list)

        except Exception as error:
            return f"Error getting orders for client ID '{clientId}': {error}"

    # ===================== APPOINTMENT FUNCTIONS =====================

    async def check_appointment_availability(self, date: str, timeSlots: Optional[List[str]] = None) -> str:
        """Check appointment availability for a specific date and optionally specific time slots."""
        try:
            logger.info(f"=======> checking appointment availability for date: {date}")

            # Build query parameters
            params = {"date": date}
            if timeSlots:
                params["timeSlots"] = ",".join(timeSlots)

            # Build URL with query params
            url = f"{API_BASE_URL}/appointments/availability/check"
            if params:
                url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])

            response = await fetch_with_timeout(url)

            if response.status_code != 200:
                raise Exception(f"Failed to check availability, status code: {response.status_code}")

            availability_data = response.json()

            if availability_data.get("error"):
                return f"Error checking availability: {availability_data['error']}"

            if timeSlots:
                # Return specific slot availability
                available = availability_data.get("available", [])
                unavailable = availability_data.get("unavailable", [])

                if not available:
                    return f"I'm sorry, none of the requested time slots ({', '.join(timeSlots)}) are available on {date}. Let me check what times are available for that day."
                elif not unavailable:
                    return f"Great news! All your requested time slots are available on {date}: {', '.join(available)}. Which time would you prefer?"
                else:
                    return f"On {date}, these times are available: {', '.join(available)}. Unfortunately, these times are already booked: {', '.join(unavailable)}. Which available time works best for you?"
            else:
                # Return all available slots
                available_slots = availability_data.get("availableSlots", [])

                if not available_slots:
                    return f"I'm sorry, but we don't have any available appointments on {date}. Would you like me to check a different date?"
                else:
                    return f"Here are the available appointment times on {date}: {', '.join(available_slots)}. Which time would work best for you?"

        except Exception as error:
            logger.error(f"=======> checkAppointmentAvailability error: {error}")
            return f"I apologize, but I'm having trouble checking availability right now: {error}. Please try again or call us directly."

    async def create_appointment(self, patientName: str, isReturningPatient: bool, appointmentType: str, appointmentTime: str, reminderPreference: str) -> str:
        """Create a new dental appointment."""
        try:
            logger.info(f"=======> creating appointment for: {patientName} ({appointmentType}) at {appointmentTime}")
            
            response = await fetch_with_timeout(
                f"{API_BASE_URL}/appointments",
                method="POST",
                json_data={
                    "patientName": patientName,
                    "isReturningPatient": isReturningPatient,
                    "appointmentType": appointmentType,
                    "appointmentTime": appointmentTime,
                    "reminderPreference": reminderPreference,
                    "status": "confirmed"
                }
            )

            if response.status_code != 200:
                raise Exception(f"Failed to create appointment, status code: {response.status_code}")

            appointment_data = response.json()
            reminder_text = "" if reminderPreference == "none" else f" We'll send you a {reminderPreference} reminder the day before."
            return f"Perfect! I've booked you in for {appointmentTime}.{reminder_text} Your appointment ID is {appointment_data.get('id', 'N/A')}. Is there anything else I can help you with today?"

        except Exception as error:
            return f"I apologize, but there was an error creating your appointment: {error}. Please try again or call us directly."

    # ===================== LEAD FUNCTIONS =====================

    async def capture_lead(self, call_outcome: str, coverage_type: Optional[str] = None, premium_change: Optional[str] = None, 
                          zip_code: Optional[str] = None, age: Optional[int] = None, tobacco_user: Optional[bool] = None,
                          objection_text: Optional[str] = None, first_name: Optional[str] = None, 
                          last_name: Optional[str] = None, phone: Optional[str] = None) -> str:
        """Capture health insurance lead information from the sales call."""
        try:
            logger.info(f"=======> capturing lead with outcome: {call_outcome}")
            
            lead_data = {
                "call_outcome": call_outcome,
                "call_datetime": datetime.now().isoformat()
            }
            
            # Add optional fields if provided
            if coverage_type:
                lead_data["coverage_type"] = coverage_type
            if premium_change:
                lead_data["premium_change"] = premium_change
            if zip_code:
                lead_data["zip_code"] = zip_code
            if age is not None:
                lead_data["age"] = age
            if tobacco_user is not None:
                lead_data["tobacco_user"] = tobacco_user
            if objection_text:
                lead_data["objection_text"] = objection_text
            if first_name:
                lead_data["first_name"] = first_name
            if last_name:
                lead_data["last_name"] = last_name
            if phone:
                lead_data["phone"] = phone

            response = await fetch_with_timeout(
                f"{API_BASE_URL}/leads",
                method="POST",
                json_data=lead_data
            )

            if response.status_code != 200:
                raise Exception(f"Failed to capture lead, status code: {response.status_code}")

            lead_response = response.json()

            # Return appropriate response based on call outcome
            if call_outcome == "completed":
                return "Lead captured successfully! The prospect will receive a text with their health insurance options."
            elif call_outcome == "voicemail":
                return "Voicemail lead captured. The prospect can call back if interested."
            elif call_outcome == "reschedule":
                return "Lead captured with reschedule request. Follow up at the agreed time."
            elif call_outcome == "declined":
                return "Lead captured with declined status. Thank you for the professional call."
            else:
                return "Lead information captured successfully."

        except Exception as error:
            logger.error(f"=======> captureLead error: {error}")
            return f"Error capturing lead: {error}. Please try again or contact support."

    # ===================== AIRLINE FUNCTIONS =====================

    async def change_booking(self, bookingCode: str, newDate: Optional[str] = None, newFlightNumber: Optional[str] = None) -> str:
        """Change an existing flight booking (modify date, flight number, etc.)."""
        try:
            logger.info(f"=======> changing booking {bookingCode}")

            request_body = {"bookingCode": bookingCode}

            if newDate:
                # Convert date to ISO string format
                try:
                    date = datetime.fromisoformat(newDate.replace('Z', '+00:00'))
                    request_body["newDate"] = date.isoformat()
                except ValueError:
                    return "Invalid date format. Please provide date in YYYY-MM-DD format."

            if newFlightNumber:
                request_body["newFlightNumber"] = newFlightNumber

            if not newDate and not newFlightNumber:
                return "Please specify what you'd like to change - either a new date or flight number."

            response = await fetch_with_timeout(
                f"{API_BASE_URL}/airline/booking/change",
                method="POST",
                json_data=request_body
            )

            if response.status_code != 200:
                raise Exception(f"Failed to change booking, status code: {response.status_code}")

            result = response.json()

            if not result.get("success"):
                return f"I'm sorry, I wasn't able to make that change: {result.get('message', 'Unknown error')}"

            booking = result.get("data", {})
            change_details = []
            if newDate:
                change_details.append(f"date to {booking.get('date', newDate)}")
            if newFlightNumber:
                change_details.append(f"flight to {booking.get('flightNumber', newFlightNumber)}")

            return f"Perfect! I've successfully updated your booking {bookingCode} to change the {' and '.join(change_details)}. Your updated reservation is from {booking.get('origin', 'N/A')} to {booking.get('destination', 'N/A')}. Is there anything else I can help you with?"

        except Exception as error:
            logger.error(f"=======> changeBooking error: {error}")
            return f"I apologize, but I'm having trouble processing that booking change right now: {error}. Please try again or I can connect you with a supervisor."

    async def check_in_passenger(self, bookingCode: Optional[str] = None, loyaltyNumber: Optional[str] = None, seatPreference: Optional[str] = None) -> str:
        """Check in a passenger for their flight and assign seats."""
        try:
            identifier = f"booking {bookingCode}" if bookingCode else f"loyalty number {loyaltyNumber}"
            logger.info(f"=======> checking in passenger with {identifier}")

            request_body = {}
            if bookingCode:
                request_body["bookingCode"] = bookingCode
            if loyaltyNumber:
                request_body["loyaltyNumber"] = loyaltyNumber
            if seatPreference:
                request_body["seatPreference"] = seatPreference

            response = await fetch_with_timeout(
                f"{API_BASE_URL}/airline/checkin",
                method="POST",
                json_data=request_body
            )

            if response.status_code != 200:
                raise Exception(f"Failed to check in passenger, status code: {response.status_code}")

            result = response.json()

            if not result.get("success"):
                return f"I'm sorry, I wasn't able to complete your check-in: {result.get('message', 'Unknown error')}"

            checkin_data = result.get("data", {})
            assigned_seat = checkin_data.get("assignedSeat", "N/A")
            flight_number = checkin_data.get("flightNumber", "N/A")
            
            seat_text = f"your preferred seat {assigned_seat}" if seatPreference and assigned_seat == seatPreference else f"seat {assigned_seat}"

            boarding_time = checkin_data.get("boardingTime")
            if boarding_time:
                try:
                    boarding_dt = datetime.fromisoformat(boarding_time.replace('Z', '+00:00'))
                    boarding_text = boarding_dt.strftime("%I:%M %p on %B %d, %Y")
                except:
                    boarding_text = str(boarding_time)
            else:
                boarding_text = "the scheduled time"

            return f"Excellent! I've successfully checked you in for flight {flight_number}. You're assigned to {seat_text}. Please arrive at the gate by {boarding_text} for boarding. Have a great flight!"

        except Exception as error:
            logger.error(f"=======> checkInPassenger error: {error}")
            return f"I apologize, but I'm having trouble with the check-in process right now: {error}. Please try again or visit the check-in counter at the airport."

    async def report_lost_baggage(self, baggageCode: str, passengerName: str, lastSeenLocation: str) -> str:
        """Report lost or missing baggage and create a tracking report."""
        try:
            logger.info(f"=======> reporting lost baggage {baggageCode} for {passengerName}")

            request_body = {
                "baggageCode": baggageCode,
                "passengerName": passengerName,
                "lastSeenLocation": lastSeenLocation
            }

            response = await fetch_with_timeout(
                f"{API_BASE_URL}/airline/baggage/lost",
                method="POST",
                json_data=request_body
            )

            if response.status_code != 200:
                raise Exception(f"Failed to report lost baggage, status code: {response.status_code}")

            result = response.json()

            if not result.get("success"):
                return f"I'm sorry, I wasn't able to file that baggage report: {result.get('message', 'Unknown error')}"

            report_data = result.get("data", {})
            report_number = report_data.get("reportNumber", "N/A")
            current_location = report_data.get("currentLocation", lastSeenLocation)
            estimated_recovery = report_data.get("estimatedRecoveryTime", "24-48 hours")

            return f"I've successfully filed a lost baggage report for you. Your report number is {report_number}. We show the bag was last seen at {current_location}. Our team will begin searching immediately, and we typically recover lost bags within {estimated_recovery}. I'll make sure to keep you updated on the progress. Is there anything else I can help you with today?"

        except Exception as error:
            logger.error(f"=======> reportLostBaggage error: {error}")
            return f"I apologize, but I'm having trouble filing the baggage report right now: {error}. Please try again or visit our baggage services counter for immediate assistance."

    # ===================== CONSULTATION FUNCTIONS =====================

    async def get_timezone_from_location(self, location: str) -> str:
        """Get timezone from user location using basic location matching."""
        try:
            # If already a timezone format, return as-is
            if "/" in location and any(location.startswith(tz) for tz in ["America/", "Europe/", "Asia/", "Australia/"]):
                return location

            logger.info(f"=======> Getting timezone for location: {location}")
            
            # Basic location to timezone mapping
            location_lower = location.lower()
            if "buenos aires" in location_lower or "argentina" in location_lower:
                return "America/Argentina/Buenos_Aires"
            elif "new york" in location_lower or " ny" in location_lower:
                return "America/New_York"
            elif "los angeles" in location_lower or "california" in location_lower:
                return "America/Los_Angeles"
            elif "chicago" in location_lower:
                return "America/Chicago"
            elif "denver" in location_lower:
                return "America/Denver"
            elif "london" in location_lower or " uk" in location_lower:
                return "Europe/London"
            elif "paris" in location_lower or "france" in location_lower:
                return "Europe/Paris"
            elif "tokyo" in location_lower or "japan" in location_lower:
                return "Asia/Tokyo"
            else:
                # Ultimate fallback
                logger.info(f"=======> Using fallback timezone: America/New_York")
                return "America/New_York"

        except Exception as error:
            logger.warning(f"=======> Failed to get timezone for '{location}': {error}")
            return "America/New_York"

    def convert_to_24_hour(self, time_str: str) -> str:
        """Convert 12-hour time to 24-hour format."""
        clean_time = time_str.strip().upper()
        
        # If already in 24-hour format
        if ":" in clean_time and "AM" not in clean_time and "PM" not in clean_time:
            return clean_time
        
        hour = 0
        minute = 0
        is_pm = "PM" in clean_time
        
        # Extract hour and minute
        time_only = clean_time.replace(" AM", "").replace(" PM", "")
        parts = time_only.split(":")
        
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        
        # Convert to 24-hour format
        if is_pm and hour != 12:
            hour += 12
        elif not is_pm and hour == 12:
            hour = 0
        
        return f"{hour:02d}:{minute:02d}"

    async def check_calendar_availability(self, date: str, startTime: str, location: str) -> str:
        """Check calendar for exact start time conflicts."""
        try:
            # Get timezone from user location
            timezone = await self.get_timezone_from_location(location)
            logger.info(f"=======> checking calendar availability for date: {date}, startTime: {startTime}, location: {location}, timezone: {timezone}")

            # Validate that startTime is provided
            if not startTime or not startTime.strip():
                logger.error("ERROR: checkCalendarAvailability called without startTime parameter!")
                return "ERROR: startTime parameter is required! You must provide a specific time like '2:00 PM' or '14:00' to check for conflicts."

            # Fetch all events
            response = await fetch_with_timeout(f"{API_BASE_URL}/calendar/events")

            if response.status_code != 200:
                raise Exception(f"Failed to fetch calendar events, status code: {response.status_code}")

            events = response.json()
            
            try:
                requested_date = datetime.fromisoformat(date.replace('Z', '+00:00') if 'Z' in date else date)
            except ValueError:
                return "Invalid date format. Please provide date in YYYY-MM-DD format."

            # Convert the user's time to 24-hour format for comparison
            requested_time_24hour = self.convert_to_24_hour(startTime)
            logger.info(f"=======> Converted '{startTime}' to 24-hour format: '{requested_time_24hour}' in timezone: {timezone}")

            # Filter events for the requested date and check for conflicts
            conflicts = []
            for event in events:
                try:
                    event_start = datetime.fromisoformat(event["startDateTime"].replace('Z', '+00:00'))
                    
                    # Check if event is on the same date
                    if event_start.date() == requested_date.date():
                        # Convert event time to comparison format
                        event_time_24hour = event_start.strftime("%H:%M")
                        
                        logger.info(f"=======> Checking event: {event.get('title', 'Untitled')} at {event_time_24hour} vs requested {requested_time_24hour}")
                        
                        # Check for exact start time match
                        if event_time_24hour == requested_time_24hour:
                            conflicts.append(event)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping invalid event: {e}")
                    continue

            logger.info(f"=======> Found {len(conflicts)} conflicts for requested time {startTime} ({requested_time_24hour}) in timezone {timezone}")

            if conflicts:
                conflict_times = []
                for event in conflicts:
                    try:
                        start = datetime.fromisoformat(event["startDateTime"].replace('Z', '+00:00'))
                        end = datetime.fromisoformat(event["endDateTime"].replace('Z', '+00:00'))
                        title = event.get("title", "Untitled")
                        conflict_times.append(f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')} ({title})")
                    except:
                        conflict_times.append("Unknown time")

                return f"I'm sorry, the requested time {startTime} on {date} is already booked with: {', '.join(conflict_times)}. Would you like to try a different time?"
            else:
                return f"Great news! The time {startTime} on {date} is available for scheduling."

        except Exception as error:
            logger.error(f"=======> checkCalendarAvailability error: {error}")
            return f"I apologize, but I'm having trouble checking calendar availability right now: {error}. Please try again or suggest a time and I'll do my best to accommodate."

    async def schedule_consultation(self, client_name: str, contact_method: str, project_description: str, consultation_outcome: str,
                                  industry: Optional[str] = None, business_challenges: Optional[str] = None, 
                                  timeline: Optional[str] = None, budget_range: Optional[str] = None,
                                  preferred_date: Optional[str] = None, preferred_time: Optional[str] = None) -> str:
        """Schedule an AI consultation with a potential client and create a calendar event."""
        try:
            logger.info(f"=======> scheduling consultation for {client_name} with outcome: {consultation_outcome}")

            # Determine consultation type based on project description
            consultation_type = "AI Strategy Session"
            project_lower = project_description.lower()
            if "chatbot" in project_lower or "nlp" in project_lower:
                consultation_type = "AI Chatbot Consultation"
            elif "automation" in project_lower or "workflow" in project_lower:
                consultation_type = "AI Automation Consultation"
            elif "data" in project_lower or "analytics" in project_lower:
                consultation_type = "AI Data Analytics Consultation"
            elif "vision" in project_lower or "image" in project_lower:
                consultation_type = "AI Computer Vision Consultation"

            # Build consultation summary
            consultation_summary_parts = [
                f"Client: {client_name}",
                f"Contact: {contact_method}",
                f"Project: {project_description}"
            ]
            if industry:
                consultation_summary_parts.append(f"Industry: {industry}")
            if business_challenges:
                consultation_summary_parts.append(f"Challenges: {business_challenges}")
            if timeline:
                consultation_summary_parts.append(f"Timeline: {timeline}")
            if budget_range:
                consultation_summary_parts.append(f"Budget: {budget_range}")

            consultation_summary = "\n".join(consultation_summary_parts)

            # If scheduling a consultation, create calendar event
            if consultation_outcome == "scheduled" and preferred_date and preferred_time:
                try:
                    # Parse consultation datetime
                    consultation_date = datetime.fromisoformat(preferred_date.replace('Z', '+00:00') if 'Z' in preferred_date else preferred_date)
                    
                    # For time parsing, create a datetime object
                    time_24hour = self.convert_to_24_hour(preferred_time)
                    hour, minute = map(int, time_24hour.split(':'))
                    consultation_datetime = consultation_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # Validate date parsing
                    if consultation_datetime < datetime.now():
                        return f"Error: The consultation date and time must be in the future."
                    
                    end_datetime = consultation_datetime + timedelta(minutes=30)  # 30 minutes later

                    # First check for conflicts
                    logger.info(f"=======> About to check availability for {preferred_date}, startTime: {preferred_time}")
                    availability_check = await self.check_calendar_availability(preferred_date, preferred_time, "America/New_York")
                    
                    if "already booked with" in availability_check:
                        return f"I'm sorry, but {preferred_time} on {preferred_date} is not available. {availability_check} Please choose a different time and I'll check availability again."

                    # Validate that we have a valid email
                    is_email = "@" in contact_method
                    if not is_email:
                        logger.warning("Contact method is not an email, skipping calendar event creation")
                    else:
                        calendar_response = await fetch_with_timeout(
                            f"{API_BASE_URL}/calendar/events",
                            method="POST",
                            json_data={
                                "title": f"{consultation_type} - {client_name}",
                                "description": consultation_summary,
                                "attendeeEmail": contact_method,
                                "startDateTime": consultation_datetime.isoformat(),
                                "endDateTime": end_datetime.isoformat(),
                                "timeZone": "America/New_York",
                                "location": "Nova Node AI - Video Call",
                                "status": "scheduled"
                            }
                        )

                        if calendar_response.status_code != 200:
                            error_text = await calendar_response.text()
                            logger.error(f"Failed to create calendar event: {calendar_response.status_code} - {error_text}")
                        else:
                            calendar_event = await calendar_response.json()
                            logger.info(f"Calendar event created successfully: {calendar_event.get('id', 'Unknown')}")

                except Exception as error:
                    logger.error(f"Error creating calendar event: {error}")

            # Return appropriate response based on outcome
            if consultation_outcome == "scheduled":
                return f"Perfect! I've scheduled your {consultation_type} for {preferred_date} at {preferred_time}. You'll receive a calendar invite at {contact_method} shortly. Our team will prepare a custom proposal based on your {project_description} project. Looking forward to helping Nova Node AI build something amazing for you!"
            elif consultation_outcome == "interested":
                return f"Thank you for your interest in Nova Node AI! I've captured all your project details about {project_description}. We'll keep your information and reach out when you're ready to move forward. Feel free to contact us anytime!"
            elif consultation_outcome == "not_ready":
                return f"No problem at all! AI projects benefit from good planning. I've saved your project details about {project_description}, and we'll be here when you're ready to start. Thank you for considering Nova Node AI!"
            elif consultation_outcome == "declined":
                return "Thank you for your time today. If your AI needs change in the future, Nova Node AI will be here to help. Have a great day!"
            else:
                return "Thank you for sharing your AI project requirements with Nova Node AI. We've captured all the details and will follow up accordingly."

        except Exception as error:
            logger.error(f"=======> scheduleConsultation error: {error}")
            return f"I apologize, but I'm having trouble processing your consultation request right now: {error}. Please try again or contact Nova Node AI directly. We'd still love to help with your AI project!"

    async def handle_function_call(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Handle function calls from the LLM."""
        try:
            if function_name == "checkClientId":
                return await self.check_client_id(arguments["clientId"])
            elif function_name == "searchProducts":
                return await self.search_products(arguments["query"])
            elif function_name == "createOrder":
                return await self.create_order(arguments["clientId"], arguments["products"])
            elif function_name == "createSingleProductOrder":
                return await self.create_single_product_order(arguments["clientId"], arguments["productId"], arguments["quantity"])
            elif function_name == "finishOrder":
                return await self.finish_order(arguments["orderId"], arguments["date"], arguments["address"])
            elif function_name == "getOrdersByClientId":
                return await self.get_orders_by_client_id(arguments["clientId"])
            elif function_name == "createAppointment":
                return await self.create_appointment(
                    arguments["patientName"], arguments["isReturningPatient"], 
                    arguments["appointmentType"], arguments["appointmentTime"], arguments["reminderPreference"]
                )
            elif function_name == "checkAppointmentAvailability":
                return await self.check_appointment_availability(arguments["date"], arguments.get("timeSlots"))
            elif function_name == "captureLead":
                return await self.capture_lead(
                    arguments["call_outcome"], arguments.get("coverage_type"), arguments.get("premium_change"),
                    arguments.get("zip_code"), arguments.get("age"), arguments.get("tobacco_user"),
                    arguments.get("objection_text"), arguments.get("first_name"), arguments.get("last_name"), arguments.get("phone")
                )
            elif function_name == "changeBooking":
                return await self.change_booking(arguments["bookingCode"], arguments.get("newDate"), arguments.get("newFlightNumber"))
            elif function_name == "checkInPassenger":
                return await self.check_in_passenger(arguments.get("bookingCode"), arguments.get("loyaltyNumber"), arguments.get("seatPreference"))
            elif function_name == "reportLostBaggage":
                return await self.report_lost_baggage(arguments["baggageCode"], arguments["passengerName"], arguments["lastSeenLocation"])
            elif function_name == "scheduleConsultation":
                return await self.schedule_consultation(
                    arguments["client_name"], arguments["contact_method"], arguments["project_description"], arguments["consultation_outcome"],
                    arguments.get("industry"), arguments.get("business_challenges"), arguments.get("timeline"), arguments.get("budget_range"),
                    arguments.get("preferred_date"), arguments.get("preferred_time")
                )
            elif function_name == "checkCalendarAvailability":
                return await self.check_calendar_availability(arguments["date"], arguments["startTime"], arguments["location"])
            else:
                return f"Function {function_name} not implemented."
        except Exception as error:
            logger.error(f"Error handling function call {function_name}: {error}")
            return f"Error executing {function_name}: {error}"