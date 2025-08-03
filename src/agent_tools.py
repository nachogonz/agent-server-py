"""
LiveKit Function Tools Integration

This module creates a simple function calling bridge for LiveKit.
"""

import logging
from typing import List
from livekit.agents.llm import function_tool
from livekit.agents import RunContext

from .functions import FunctionContext

logger = logging.getLogger(__name__)


def build_livekit_tools(fc: FunctionContext) -> List:
    """
    Build LiveKit function tools using a simple approach.
    
    Args:
        fc: FunctionContext instance with existing function definitions
        
    Returns:
        List of LiveKit function tools
    """
    tools = []
    
    # Create individual function tools for each function
    # This approach manually creates each function to avoid signature inspection issues
    
    @function_tool()
    async def checkClientId(ctx: RunContext, clientId: str) -> str:
        """Check if a client ID exists in the database and greet the user"""
        try:
            logger.info(f"🔧 Calling checkClientId with clientId: {clientId}")
            result = await fc.handle_function_call("checkClientId", {"clientId": clientId})
            logger.info(f"✅ checkClientId completed successfully")
            return result
        except Exception as error:
            logger.error(f"❌ Error in checkClientId: {error}")
            return f"Error checking client ID: {error}"
    
    @function_tool()
    async def searchProducts(ctx: RunContext, query: str) -> str:
        """Search for products in the database using vector similarity for better precision"""
        return await fc.handle_function_call("searchProducts", {"query": query})
    
    @function_tool(
        raw_schema={
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
        }
    )
    async def createOrder(ctx: RunContext, clientId: str, products: list) -> str:
        """Create a new order for a client with products and quantities"""
        try:
            logger.info(f"🔧 Calling createOrder with clientId: {clientId}, products: {products}")
            result = await fc.handle_function_call("createOrder", {"clientId": clientId, "products": products})
            logger.info(f"✅ createOrder completed successfully")
            return result
        except Exception as error:
            logger.error(f"❌ Error in createOrder: {error}")
            return f"Error creating order: {error}"
    
    @function_tool()
    async def createSingleProductOrder(ctx: RunContext, clientId: str, productId: str, quantity: int) -> str:
        """Create a single product order for a client"""
        return await fc.handle_function_call("createSingleProductOrder", {"clientId": clientId, "productId": productId, "quantity": quantity})
    
    @function_tool()
    async def finishOrder(ctx: RunContext, orderId: str, date: str, address: str) -> str:
        """Finish an order with delivery information"""
        return await fc.handle_function_call("finishOrder", {"orderId": orderId, "date": date, "address": address})
    
    @function_tool()
    async def getOrdersByClientId(ctx: RunContext, clientId: str) -> str:
        """Get all orders for a specific client"""
        return await fc.handle_function_call("getOrdersByClientId", {"clientId": clientId})
    
    @function_tool()
    async def createAppointment(ctx: RunContext, patientName: str, isReturningPatient: bool, appointmentType: str, appointmentTime: str, reminderPreference: str) -> str:
        """Create a new appointment"""
        return await fc.handle_function_call("createAppointment", {
            "patientName": patientName,
            "isReturningPatient": isReturningPatient,
            "appointmentType": appointmentType,
            "appointmentTime": appointmentTime,
            "reminderPreference": reminderPreference
        })
    
    @function_tool(
        raw_schema={
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
    )
    async def checkAppointmentAvailability(ctx: RunContext, date: str, timeSlots: list = None) -> str:
        """Check appointment availability for a specific date"""
        try:
            logger.info(f"🔧 Calling checkAppointmentAvailability with date: {date}, timeSlots: {timeSlots}")
            result = await fc.handle_function_call("checkAppointmentAvailability", {"date": date, "timeSlots": timeSlots})
            logger.info(f"✅ checkAppointmentAvailability completed successfully")
            return result
        except Exception as error:
            logger.error(f"❌ Error in checkAppointmentAvailability: {error}")
            return f"Error checking appointment availability: {error}"
    
    @function_tool()
    async def captureLead(ctx: RunContext, call_outcome: str, coverage_type: str = None, premium_change: str = None, zip_code: str = None, age: int = None, tobacco_user: bool = None, objection_text: str = None, first_name: str = None, last_name: str = None, phone: str = None) -> str:
        """Capture a lead with call outcome and optional details"""
        return await fc.handle_function_call("captureLead", {
            "call_outcome": call_outcome,
            "coverage_type": coverage_type,
            "premium_change": premium_change,
            "zip_code": zip_code,
            "age": age,
            "tobacco_user": tobacco_user,
            "objection_text": objection_text,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone
        })
    
    @function_tool()
    async def changeBooking(ctx: RunContext, bookingCode: str, newDate: str = None, newFlightNumber: str = None) -> str:
        """Change a flight booking"""
        return await fc.handle_function_call("changeBooking", {"bookingCode": bookingCode, "newDate": newDate, "newFlightNumber": newFlightNumber})
    
    @function_tool()
    async def checkInPassenger(ctx: RunContext, bookingCode: str = None, loyaltyNumber: str = None, seatPreference: str = None) -> str:
        """Check in a passenger for their flight"""
        return await fc.handle_function_call("checkInPassenger", {"bookingCode": bookingCode, "loyaltyNumber": loyaltyNumber, "seatPreference": seatPreference})
    
    @function_tool()
    async def reportLostBaggage(ctx: RunContext, baggageCode: str, passengerName: str, lastSeenLocation: str) -> str:
        """Report lost baggage"""
        return await fc.handle_function_call("reportLostBaggage", {"baggageCode": baggageCode, "passengerName": passengerName, "lastSeenLocation": lastSeenLocation})
    
    @function_tool()
    async def scheduleConsultation(ctx: RunContext, client_name: str, contact_method: str, project_description: str, consultation_outcome: str, industry: str = None, business_challenges: str = None, timeline: str = None, budget_range: str = None, preferred_date: str = None, preferred_time: str = None) -> str:
        """Schedule a consultation for AI services"""
        return await fc.handle_function_call("scheduleConsultation", {
            "client_name": client_name,
            "contact_method": contact_method,
            "project_description": project_description,
            "consultation_outcome": consultation_outcome,
            "industry": industry,
            "business_challenges": business_challenges,
            "timeline": timeline,
            "budget_range": budget_range,
            "preferred_date": preferred_date,
            "preferred_time": preferred_time
        })
    
    @function_tool()
    async def checkCalendarAvailability(ctx: RunContext, date: str, startTime: str, location: str) -> str:
        """Check calendar availability for a specific date and time"""
        return await fc.handle_function_call("checkCalendarAvailability", {"date": date, "startTime": startTime, "location": location})
    
    # Add all tools to the list
    tools = [
        checkClientId, searchProducts, createOrder, createSingleProductOrder, finishOrder, getOrdersByClientId,
        createAppointment, checkAppointmentAvailability, captureLead, changeBooking, checkInPassenger, 
        reportLostBaggage, scheduleConsultation, checkCalendarAvailability
    ]
    
    logger.info(f"✅ Built {len(tools)} LiveKit function tools")
    return tools