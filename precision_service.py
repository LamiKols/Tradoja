"""
Precision Agriculture Service
Provides field analysis, crop recommendations, and agronomy calculations
"""

import json
from datetime import datetime, date
from calendar import monthrange
import math


class PrecisionAgricultureService:
    """Service for precision agriculture calculations and recommendations"""
    
    def __init__(self):
        # Crop data with agronomy parameters
        self.crop_data = {
            'rice': {
                'name': 'Rice',
                'optimal_seasons': ['wet', 'dry'],
                'planting_months': [6, 7, 8, 11, 12, 1],  # June-Aug (wet), Nov-Jan (dry)
                'fertilizer_kg_ha': {'base': 120, 'range': [80, 200]},
                'irrigation_l_ha': {'base': 15000, 'range': [12000, 20000]},
                'yield_tons_ha': {'base': 4.5, 'range': [3.0, 7.0]},
                'growth_days': 120,
                'soil_types': ['clay', 'loam', 'sandy-loam'],
                'spacing_cm': 20
            },
            'maize': {
                'name': 'Maize/Corn',
                'optimal_seasons': ['wet'],
                'planting_months': [4, 5, 6, 7],  # April-July
                'fertilizer_kg_ha': {'base': 150, 'range': [100, 250]},
                'irrigation_l_ha': {'base': 8000, 'range': [6000, 12000]},
                'yield_tons_ha': {'base': 5.0, 'range': [3.5, 8.0]},
                'growth_days': 90,
                'soil_types': ['loam', 'sandy-loam', 'clay-loam'],
                'spacing_cm': 25
            },
            'cassava': {
                'name': 'Cassava',
                'optimal_seasons': ['wet', 'dry'],
                'planting_months': [4, 5, 6, 7, 8, 9],  # April-September
                'fertilizer_kg_ha': {'base': 80, 'range': [50, 120]},
                'irrigation_l_ha': {'base': 5000, 'range': [3000, 8000]},
                'yield_tons_ha': {'base': 15.0, 'range': [10.0, 25.0]},
                'growth_days': 365,
                'soil_types': ['sandy', 'sandy-loam', 'loam'],
                'spacing_cm': 100
            },
            'yam': {
                'name': 'Yam',
                'optimal_seasons': ['wet'],
                'planting_months': [4, 5, 6],  # April-June
                'fertilizer_kg_ha': {'base': 100, 'range': [70, 150]},
                'irrigation_l_ha': {'base': 6000, 'range': [4000, 9000]},
                'yield_tons_ha': {'base': 12.0, 'range': [8.0, 20.0]},
                'growth_days': 270,
                'soil_types': ['loam', 'clay-loam', 'sandy-loam'],
                'spacing_cm': 100
            },
            'tomato': {
                'name': 'Tomato',
                'optimal_seasons': ['dry', 'wet'],
                'planting_months': [10, 11, 12, 1, 2, 3],  # Oct-Mar
                'fertilizer_kg_ha': {'base': 180, 'range': [120, 250]},
                'irrigation_l_ha': {'base': 12000, 'range': [8000, 18000]},
                'yield_tons_ha': {'base': 25.0, 'range': [15.0, 40.0]},
                'growth_days': 75,
                'soil_types': ['loam', 'sandy-loam', 'clay-loam'],
                'spacing_cm': 50
            },
            'pepper': {
                'name': 'Pepper',
                'optimal_seasons': ['dry', 'wet'],
                'planting_months': [10, 11, 12, 1, 2, 3],  # Oct-Mar
                'fertilizer_kg_ha': {'base': 120, 'range': [80, 180]},
                'irrigation_l_ha': {'base': 8000, 'range': [6000, 12000]},
                'yield_tons_ha': {'base': 8.0, 'range': [5.0, 15.0]},
                'growth_days': 90,
                'soil_types': ['loam', 'sandy-loam', 'clay-loam'],
                'spacing_cm': 40
            },
            'okra': {
                'name': 'Okra',
                'optimal_seasons': ['wet', 'dry'],
                'planting_months': [3, 4, 5, 6, 7, 8],  # March-August
                'fertilizer_kg_ha': {'base': 90, 'range': [60, 130]},
                'irrigation_l_ha': {'base': 6000, 'range': [4000, 9000]},
                'yield_tons_ha': {'base': 6.0, 'range': [4.0, 10.0]},
                'growth_days': 60,
                'soil_types': ['loam', 'sandy-loam', 'clay-loam'],
                'spacing_cm': 30
            }
        }
        
        # Soil type modifiers
        self.soil_modifiers = {
            'clay': {'fertilizer': 1.1, 'irrigation': 0.9, 'yield': 1.0},
            'loam': {'fertilizer': 1.0, 'irrigation': 1.0, 'yield': 1.1},
            'sandy-loam': {'fertilizer': 0.9, 'irrigation': 1.1, 'yield': 1.0},
            'sandy': {'fertilizer': 0.8, 'irrigation': 1.3, 'yield': 0.9},
            'clay-loam': {'fertilizer': 1.05, 'irrigation': 0.95, 'yield': 1.05}
        }
        
        # Irrigation system efficiency
        self.irrigation_efficiency = {
            'drip': 0.9,
            'sprinkler': 0.8,
            'furrow': 0.6,
            'flood': 0.5,
            'none': 1.5  # Rain-fed requires higher estimates
        }
        
        # Fertilizer type efficiency
        self.fertilizer_efficiency = {
            'organic': 0.8,
            'npk': 1.0,
            'urea': 1.1,
            'compound': 1.05,
            'none': 0.0
        }
    
    def get_crop_choices(self):
        """Get crop choices for forms"""
        choices = [('', 'Select Crop Type')]
        for key, data in self.crop_data.items():
            choices.append((key, data['name']))
        return choices
    
    def get_soil_choices(self):
        """Get soil type choices for forms"""
        return [
            ('', 'Select Soil Type'),
            ('clay', 'Clay'),
            ('loam', 'Loam'),
            ('sandy-loam', 'Sandy Loam'),
            ('sandy', 'Sandy'),
            ('clay-loam', 'Clay Loam')
        ]
    
    def get_irrigation_choices(self):
        """Get irrigation type choices for forms"""
        return [
            ('', 'Select Irrigation Type'),
            ('drip', 'Drip Irrigation'),
            ('sprinkler', 'Sprinkler'),
            ('furrow', 'Furrow Irrigation'),
            ('flood', 'Flood Irrigation'),
            ('none', 'Rain-fed (No Irrigation)')
        ]
    
    def get_fertilizer_choices(self):
        """Get fertilizer type choices for forms"""
        return [
            ('', 'Select Fertilizer Type'),
            ('npk', 'NPK Compound'),
            ('urea', 'Urea'),
            ('organic', 'Organic/Compost'),
            ('compound', 'Compound Fertilizer'),
            ('none', 'No Fertilizer')
        ]
    
    def calculate_field_area(self, coordinates):
        """Calculate field area from polygon coordinates using shoelace formula"""
        if not coordinates or len(coordinates) < 3:
            return 0.0
        
        try:
            # Convert to radians and calculate area using spherical excess
            def deg_to_rad(deg):
                return deg * math.pi / 180
            
            area = 0.0
            n = len(coordinates)
            
            for i in range(n):
                j = (i + 1) % n
                lat1, lon1 = deg_to_rad(coordinates[i][0]), deg_to_rad(coordinates[i][1])
                lat2, lon2 = deg_to_rad(coordinates[j][0]), deg_to_rad(coordinates[j][1])
                
                area += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
            
            area = abs(area) * 6378137 * 6378137 / 2  # Earth radius squared
            return area / 10000  # Convert to hectares
            
        except Exception as e:
            # Fallback: simple polygon area calculation
            return self._simple_polygon_area(coordinates)
    
    def _simple_polygon_area(self, coordinates):
        """Simple polygon area calculation as fallback"""
        if len(coordinates) < 3:
            return 0.0
        
        area = 0.0
        n = len(coordinates)
        
        for i in range(n):
            j = (i + 1) % n
            area += coordinates[i][0] * coordinates[j][1]
            area -= coordinates[j][0] * coordinates[i][1]
        
        # Convert to approximate hectares (rough estimation)
        return abs(area) / 2 * 0.0001
    
    def calculate_recommendations(self, crop_type, field_size_ha, soil_type, 
                                irrigation_type, fertilizer_type, planting_date=None):
        """Calculate precision agriculture recommendations"""
        
        if crop_type not in self.crop_data:
            return self._default_recommendations()
        
        crop = self.crop_data[crop_type]
        
        # Base calculations
        base_fertilizer = crop['fertilizer_kg_ha']['base']
        base_irrigation = crop['irrigation_l_ha']['base']
        base_yield = crop['yield_tons_ha']['base']
        
        # Apply soil modifiers
        soil_mod = self.soil_modifiers.get(soil_type, {'fertilizer': 1.0, 'irrigation': 1.0, 'yield': 1.0})
        fertilizer_kg_ha = base_fertilizer * soil_mod['fertilizer']
        irrigation_l_ha = base_irrigation * soil_mod['irrigation']
        estimated_yield = base_yield * soil_mod['yield']
        
        # Apply irrigation efficiency
        irrigation_eff = self.irrigation_efficiency.get(irrigation_type, 1.0)
        irrigation_l_ha *= irrigation_eff
        
        # Apply fertilizer efficiency
        fertilizer_eff = self.fertilizer_efficiency.get(fertilizer_type, 1.0)
        fertilizer_kg_ha *= fertilizer_eff
        estimated_yield *= (fertilizer_eff * 0.8 + 0.2)  # Fertilizer affects yield
        
        # Calculate season fit and warnings
        season_fit, warnings = self._calculate_season_fit(crop, planting_date, soil_type)
        
        # Total requirements for the field
        total_fertilizer = fertilizer_kg_ha * field_size_ha
        total_irrigation = irrigation_l_ha * field_size_ha
        total_yield = estimated_yield * field_size_ha
        
        return {
            'fertilizer_kg_ha': round(fertilizer_kg_ha, 1),
            'irrigation_l_ha': round(irrigation_l_ha, 0),
            'estimated_yield_tons_ha': round(estimated_yield, 2),
            'total_fertilizer_kg': round(total_fertilizer, 1),
            'total_irrigation_l': round(total_irrigation, 0),
            'total_yield_tons': round(total_yield, 2),
            'season_fit': season_fit,
            'warnings': warnings,
            'planting_schedule': self._get_planting_schedule(crop, planting_date),
            'harvest_estimate': self._get_harvest_estimate(crop, planting_date)
        }
    
    def _calculate_season_fit(self, crop, planting_date, soil_type):
        """Calculate how well the planting date fits the crop's season"""
        warnings = []
        
        if not planting_date:
            return 'unknown', ['Planting date not specified']
        
        planting_month = planting_date.month
        optimal_months = crop['planting_months']
        
        if planting_month in optimal_months:
            season_fit = 'optimal'
        elif any(abs(planting_month - month) <= 1 or abs(planting_month - month) >= 11 
                for month in optimal_months):
            season_fit = 'good'
            warnings.append('Planting date is close to optimal but may affect yield')
        else:
            season_fit = 'poor'
            warnings.append('Planting date is not optimal for this crop')
        
        # Soil type compatibility
        if soil_type and soil_type not in crop['soil_types']:
            warnings.append(f'Soil type ({soil_type}) may not be optimal for {crop["name"]}')
        
        # Add seasonal advice
        current_month = datetime.now().month
        if planting_month in [6, 7, 8, 9]:  # Wet season
            warnings.append('Wet season planting - ensure good drainage')
        elif planting_month in [11, 12, 1, 2]:  # Dry season
            warnings.append('Dry season planting - irrigation is critical')
        
        return season_fit, warnings
    
    def _get_planting_schedule(self, crop, planting_date):
        """Get planting schedule recommendations"""
        if not planting_date:
            return 'Set planting date for schedule'
        
        optimal_months = [self._month_name(m) for m in crop['planting_months']]
        spacing = crop.get('spacing_cm', 30)
        
        return f"Optimal months: {', '.join(optimal_months)}. Plant spacing: {spacing}cm apart."
    
    def _get_harvest_estimate(self, crop, planting_date):
        """Estimate harvest date"""
        if not planting_date:
            return 'Set planting date for harvest estimate'
        
        from datetime import timedelta
        harvest_date = planting_date + timedelta(days=crop['growth_days'])
        
        return f"Estimated harvest: {harvest_date.strftime('%B %d, %Y')} ({crop['growth_days']} days)"
    
    def _month_name(self, month_num):
        """Convert month number to name"""
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        return months[month_num - 1]
    
    def _default_recommendations(self):
        """Return default recommendations for unknown crops"""
        return {
            'fertilizer_kg_ha': 100.0,
            'irrigation_l_ha': 8000.0,
            'estimated_yield_tons_ha': 5.0,
            'total_fertilizer_kg': 0.0,
            'total_irrigation_l': 0.0,
            'total_yield_tons': 0.0,
            'season_fit': 'unknown',
            'warnings': ['Crop data not available - using general estimates'],
            'planting_schedule': 'Consult local agricultural extension',
            'harvest_estimate': 'Varies by crop type'
        }
    
    def generate_field_report(self, field):
        """Generate comprehensive field report for export"""
        recommendations = self.calculate_recommendations(
            field.crop_type, field.field_size_hectares, field.soil_type,
            field.irrigation_type, field.fertilizer_type, field.planting_date
        )
        
        report = {
            'field_info': {
                'name': field.field_name,
                'crop': field.crop_type.title(),
                'size': field.formatted_size(),
                'coordinates': field.formatted_coordinates(),
                'planting_date': field.formatted_planting_date(),
                'soil_type': field.soil_type.title() if field.soil_type else 'Not specified',
                'irrigation': field.irrigation_type.title() if field.irrigation_type else 'Not specified',
                'fertilizer': field.fertilizer_type.title() if field.fertilizer_type else 'Not specified'
            },
            'recommendations': recommendations,
            'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'farmer': field.farmer.name
        }
        
        return report
    
    def get_productivity_kpis(self, fields):
        """Calculate productivity KPIs for multiple fields"""
        if not fields:
            return {}
        
        total_area = sum(f.field_size_hectares for f in fields)
        total_estimated_yield = sum(f.estimated_yield_tons_ha * f.field_size_hectares 
                                  for f in fields if f.estimated_yield_tons_ha)
        
        avg_yield_per_ha = total_estimated_yield / total_area if total_area > 0 else 0
        
        crop_distribution = {}
        for field in fields:
            crop = field.crop_type.title()
            if crop in crop_distribution:
                crop_distribution[crop] += field.field_size_hectares
            else:
                crop_distribution[crop] = field.field_size_hectares
        
        return {
            'total_fields': len(fields),
            'total_area_ha': round(total_area, 2),
            'estimated_total_yield_tons': round(total_estimated_yield, 2),
            'average_yield_per_ha': round(avg_yield_per_ha, 2),
            'crop_distribution': crop_distribution,
            'optimal_fields': len([f for f in fields if f.planting_season_fit == 'optimal']),
            'fields_with_warnings': len([f for f in fields if f.get_risk_warnings_list()])
        }