"""
Weather service for Climate-Smart Agriculture tool
Integrates with OpenWeatherMap API and provides crop recommendations
"""
import os
import requests
from typing import Dict, List, Optional, Tuple
import json


class WeatherService:
    """Service class for weather data and agricultural analysis"""
    
    def __init__(self):
        self.api_key = os.environ.get('OPENWEATHER_API_KEY')
        self.base_url = "http://api.openweathermap.org/data/2.5"
        
        # Crop recommendation database
        self.crop_recommendations = {
            'high_rainfall_high_temp': [
                {'name': 'Rice', 'description': 'Thrives in high rainfall and warm conditions', 'icon': '🌾'},
                {'name': 'Plantain', 'description': 'Excellent for tropical wet conditions', 'icon': '🍌'},
                {'name': 'Cocoyam', 'description': 'Grows well in humid, warm environments', 'icon': '🥔'},
                {'name': 'Oil Palm', 'description': 'Perfect for tropical rainforest conditions', 'icon': '🌴'}
            ],
            'high_rainfall_low_temp': [
                {'name': 'Irish Potato', 'description': 'Prefers cool, wet conditions', 'icon': '🥔'},
                {'name': 'Cabbage', 'description': 'Grows well in cool, moist weather', 'icon': '🥬'},
                {'name': 'Carrots', 'description': 'Thrives in cool temperatures with adequate moisture', 'icon': '🥕'},
                {'name': 'Lettuce', 'description': 'Cool season crop that likes moisture', 'icon': '🥬'}
            ],
            'low_rainfall_high_temp': [
                {'name': 'Millet', 'description': 'Drought-tolerant cereal for arid regions', 'icon': '🌾'},
                {'name': 'Sorghum', 'description': 'Highly drought-resistant grain crop', 'icon': '🌾'},
                {'name': 'Cowpea', 'description': 'Heat and drought tolerant legume', 'icon': '🌱'},
                {'name': 'Watermelon', 'description': 'Drought-resistant fruit crop', 'icon': '🍉'},
                {'name': 'Date Palm', 'description': 'Extremely drought tolerant tree crop', 'icon': '🌴'}
            ],
            'low_rainfall_low_temp': [
                {'name': 'Wheat', 'description': 'Cool season grain crop, moderate water needs', 'icon': '🌾'},
                {'name': 'Barley', 'description': 'Hardy grain crop for cool, dry conditions', 'icon': '🌾'},
                {'name': 'Onions', 'description': 'Cool season crop with low water requirements', 'icon': '🧅'},
                {'name': 'Garlic', 'description': 'Cold hardy with minimal water needs', 'icon': '🧄'}
            ],
            'moderate_conditions': [
                {'name': 'Maize (Corn)', 'description': 'Versatile crop for moderate conditions', 'icon': '🌽'},
                {'name': 'Yam', 'description': 'Staple root crop for tropical regions', 'icon': '🍠'},
                {'name': 'Cassava', 'description': 'Hardy root crop, drought tolerant', 'icon': '🥔'},
                {'name': 'Tomatoes', 'description': 'Popular vegetable for moderate climates', 'icon': '🍅'},
                {'name': 'Pepper', 'description': 'Heat-loving crop for warm seasons', 'icon': '🌶️'},
                {'name': 'Sweet Potato', 'description': 'Nutritious root crop, moderately drought tolerant', 'icon': '🍠'}
            ]
        }
        
        # Carbon emission factors (kg CO2 equivalent per kg of fertilizer)
        self.emission_factors = {
            'organic': 0.5,      # Lower emissions for organic fertilizers
            'synthetic': 3.0,    # Higher emissions for synthetic fertilizers
            'mixed': 1.75,       # Average of organic and synthetic
            'none': 0.0         # No emissions for no fertilizer
        }
    
    def get_current_weather(self, city: str) -> Optional[Dict]:
        """Fetch current weather data for a city"""
        if not self.api_key:
            return None
            
        try:
            url = f"{self.base_url}/weather"
            params = {
                'q': f"{city},NG",  # Focus on Nigeria
                'appid': self.api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract relevant weather information
            weather_info = {
                'city': data['name'],
                'country': data['sys']['country'],
                'temperature': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'description': data['weather'][0]['description'],
                'main': data['weather'][0]['main'],
                'icon': data['weather'][0]['icon'],
                'wind_speed': data['wind']['speed'],
                'coordinates': {
                    'lat': data['coord']['lat'],
                    'lon': data['coord']['lon']
                }
            }
            
            return weather_info
            
        except requests.exceptions.RequestException as e:
            print(f"Weather API request failed: {e}")
            return None
        except KeyError as e:
            print(f"Weather API response parsing failed: {e}")
            return None
    
    def get_weather_by_coordinates(self, lat: float, lon: float) -> Optional[Dict]:
        """Fetch weather data using GPS coordinates"""
        if not self.api_key:
            return None
            
        try:
            url = f"{self.base_url}/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            weather_info = {
                'city': data['name'],
                'country': data['sys']['country'],
                'temperature': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'description': data['weather'][0]['description'],
                'main': data['weather'][0]['main'],
                'icon': data['weather'][0]['icon'],
                'wind_speed': data['wind']['speed'],
                'coordinates': {
                    'lat': data['coord']['lat'],
                    'lon': data['coord']['lon']
                }
            }
            
            return weather_info
            
        except requests.exceptions.RequestException as e:
            print(f"Weather API request failed: {e}")
            return None
        except KeyError as e:
            print(f"Weather API response parsing failed: {e}")
            return None
    
    def get_crop_recommendations(self, weather_data: Dict, soil_type: str, 
                               soil_moisture: str) -> List[Dict]:
        """Generate crop recommendations based on weather and soil data"""
        if not weather_data:
            return self.crop_recommendations['moderate_conditions']
        
        temperature = weather_data.get('temperature', 25)
        humidity = weather_data.get('humidity', 60)
        
        # Simple classification based on temperature and humidity
        # High rainfall is approximated by high humidity (>70%)
        # High temperature is >28°C, low temperature is <22°C
        
        high_rainfall = humidity > 70 or soil_moisture == 'wet'
        high_temp = temperature > 28
        low_temp = temperature < 22
        
        # Adjust recommendations based on soil type
        soil_adjustments = {
            'clay': {'water_retention': 'high', 'drainage': 'poor'},
            'sandy': {'water_retention': 'low', 'drainage': 'excellent'},
            'loamy': {'water_retention': 'good', 'drainage': 'good'},
            'silty': {'water_retention': 'good', 'drainage': 'moderate'},
            'peaty': {'water_retention': 'high', 'drainage': 'poor'},
            'chalky': {'water_retention': 'low', 'drainage': 'excellent'}
        }
        
        # Select appropriate crop category
        if high_rainfall and high_temp:
            recommendations = self.crop_recommendations['high_rainfall_high_temp']
        elif high_rainfall and low_temp:
            recommendations = self.crop_recommendations['high_rainfall_low_temp']
        elif not high_rainfall and high_temp:
            recommendations = self.crop_recommendations['low_rainfall_high_temp']
        elif not high_rainfall and low_temp:
            recommendations = self.crop_recommendations['low_rainfall_low_temp']
        else:
            recommendations = self.crop_recommendations['moderate_conditions']
        
        # Add soil-specific advice to each recommendation
        for crop in recommendations:
            soil_props = soil_adjustments.get(soil_type, {})
            if soil_props:
                if soil_props['drainage'] == 'poor' and crop['name'] in ['Rice', 'Cocoyam']:
                    crop['soil_advice'] = f"Perfect for {soil_type} soil - retains water well"
                elif soil_props['drainage'] == 'excellent' and crop['name'] in ['Millet', 'Sorghum', 'Cassava']:
                    crop['soil_advice'] = f"Excellent for {soil_type} soil - drought tolerant"
                else:
                    crop['soil_advice'] = f"Suitable for {soil_type} soil with proper management"
            else:
                crop['soil_advice'] = "General soil management applies"
        
        return recommendations[:6]  # Return top 6 recommendations
    
    def calculate_carbon_footprint(self, field_size: float, fertilizer_type: str, 
                                 fertilizer_amount: float, estimated_yield: float) -> Dict:
        """Calculate carbon footprint based on farming practices"""
        
        # Get emission factor for fertilizer type
        emission_factor = self.emission_factors.get(fertilizer_type, 1.0)
        
        # Calculate fertilizer emissions (kg CO2 eq)
        fertilizer_emissions = field_size * fertilizer_amount * emission_factor
        
        # Estimate fuel/machinery emissions (simplified calculation)
        # Assume 50L diesel per hectare for farming operations
        diesel_per_hectare = 50  # liters
        diesel_emission_factor = 2.68  # kg CO2 per liter of diesel
        fuel_emissions = field_size * diesel_per_hectare * diesel_emission_factor
        
        # Calculate total emissions
        total_emissions = fertilizer_emissions + fuel_emissions
        
        # Calculate emissions per ton of yield
        total_yield = field_size * estimated_yield
        emissions_per_ton = total_emissions / total_yield if total_yield > 0 else 0
        
        # Carbon footprint analysis
        footprint_data = {
            'total_emissions': round(total_emissions, 2),
            'fertilizer_emissions': round(fertilizer_emissions, 2),
            'fuel_emissions': round(fuel_emissions, 2),
            'emissions_per_ton': round(emissions_per_ton, 2),
            'total_yield': round(total_yield, 2),
            'field_size': field_size,
            'recommendations': self._get_carbon_reduction_tips(fertilizer_type, emissions_per_ton)
        }
        
        return footprint_data
    
    def _get_carbon_reduction_tips(self, fertilizer_type: str, emissions_per_ton: float) -> List[str]:
        """Generate carbon footprint reduction recommendations"""
        tips = []
        
        if fertilizer_type == 'synthetic':
            tips.append("💡 Switch to organic fertilizers to reduce emissions by up to 60%")
            tips.append("🌱 Consider composting farm waste for natural fertilizer")
        
        if emissions_per_ton > 500:
            tips.append("⚡ High emissions detected - consider precision agriculture techniques")
            tips.append("🚜 Optimize machinery use and consider electric/hybrid equipment")
        
        tips.extend([
            "🌳 Plant trees around farm boundaries for carbon sequestration",
            "♻️ Practice crop rotation to improve soil health naturally",
            "💧 Use drip irrigation to reduce water and energy consumption",
            "📊 Monitor and measure your carbon footprint regularly"
        ])
        
        return tips[:4]  # Return top 4 tips
    
    def get_weather_icon_url(self, icon_code: str) -> str:
        """Generate OpenWeatherMap icon URL"""
        return f"http://openweathermap.org/img/wn/{icon_code}@2x.png"