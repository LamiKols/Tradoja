"""
Geographical Indications (GI) service for Tradoja
Manages Nigerian geographical indications registry and certification
"""
from typing import Dict, List, Optional


class GIService:
    """Service class for managing Geographical Indications"""
    
    def __init__(self):
        # Nigerian registered and potential GI products
        self.nigerian_gis = {
            'abakaliki_rice': {
                'name': 'Abakaliki Rice',
                'full_name': 'Ebonyi Abakaliki Rice',
                'region': 'Ebonyi State',
                'state': 'ebonyi',
                'description': 'Premium aromatic rice variety cultivated in the fertile soils of Abakaliki, known for its distinctive flavor and quality.',
                'status': 'registered',
                'characteristics': ['Aromatic', 'Long grain', 'Low breakage', 'High nutritional value'],
                'production_area': 'Abakaliki and surrounding areas in Ebonyi State',
                'traditional_knowledge': 'Traditional rice cultivation methods passed down through generations',
                'quality_standards': ['Moisture content below 14%', 'Minimal broken grains', 'No foreign materials'],
                'registered_date': '2019-03-15',
                'certificate_number': 'NG-GI-001'
            },
            'benue_yam': {
                'name': 'Benue Yam',
                'full_name': 'Benue White Yam',
                'region': 'Benue State',
                'state': 'benue',
                'description': 'High-quality white yam (Dioscorea rotundata) from the fertile Middle Belt region, renowned for its size and taste.',
                'status': 'registered',
                'characteristics': ['Large tuber size', 'White flesh', 'Sweet taste', 'Long storage life'],
                'production_area': 'Benue State and adjacent areas',
                'traditional_knowledge': 'Traditional yam cultivation and storage techniques',
                'quality_standards': ['Minimum weight of 2kg per tuber', 'No pest damage', 'Proper curing'],
                'registered_date': '2020-07-22',
                'certificate_number': 'NG-GI-002'
            },
            'ogun_cassava': {
                'name': 'Ogun Cassava',
                'full_name': 'Ogun State Cassava',
                'region': 'Ogun State',
                'state': 'ogun',
                'description': 'High-yielding cassava variety from Ogun State, known for its starch content and processing quality.',
                'status': 'registered',
                'characteristics': ['High starch content', 'Disease resistant', 'High yield', 'Good processing quality'],
                'production_area': 'Ogun State agricultural zones',
                'traditional_knowledge': 'Traditional cassava cultivation and processing methods',
                'quality_standards': ['Starch content above 25%', 'Low cyanide content', 'No rot or damage'],
                'registered_date': '2020-11-10',
                'certificate_number': 'NG-GI-003'
            },
            'jos_plateau_irish_potato': {
                'name': 'Jos Plateau Irish Potato',
                'full_name': 'Jos Plateau Irish Potato',
                'region': 'Plateau State',
                'state': 'plateau',
                'description': 'Cool-climate Irish potatoes grown on the Jos Plateau, valued for their unique taste and quality.',
                'status': 'registered',
                'characteristics': ['Unique flavor', 'Firm texture', 'Good storage quality', 'Adapted to cool climate'],
                'production_area': 'Jos Plateau and surrounding highlands',
                'traditional_knowledge': 'Highland farming techniques adapted to local conditions',
                'quality_standards': ['Uniform size', 'No sprouting', 'Free from diseases'],
                'registered_date': '2021-02-28',
                'certificate_number': 'NG-GI-004'
            },
            'sokoto_onion': {
                'name': 'Sokoto Onion',
                'full_name': 'Sokoto Red Onion',
                'region': 'Sokoto State',
                'state': 'sokoto',
                'description': 'Premium red onions from the Sokoto river valley, known for their pungency and storage quality.',
                'status': 'registered',
                'characteristics': ['Deep red color', 'Strong flavor', 'Excellent storage', 'Large bulb size'],
                'production_area': 'Sokoto and Kebbi river valleys',
                'traditional_knowledge': 'Traditional dry season cultivation techniques',
                'quality_standards': ['Bulb diameter minimum 6cm', 'No sprouting', 'Proper curing'],
                'registered_date': '2021-05-15',
                'certificate_number': 'NG-GI-005'
            },
            'cross_river_cocoa': {
                'name': 'Cross River Cocoa',
                'full_name': 'Cross River Premium Cocoa',
                'region': 'Cross River State',
                'state': 'cross-river',
                'description': 'Fine flavor cocoa beans from Cross River State, distinguished by their unique taste profile.',
                'status': 'registered',
                'characteristics': ['Fine flavor profile', 'Low acidity', 'Floral notes', 'Premium quality'],
                'production_area': 'Cross River State cocoa belt',
                'traditional_knowledge': 'Traditional cocoa cultivation and fermentation practices',
                'quality_standards': ['Bean size grade 1', 'Fermentation index above 1.2', 'Moisture below 7.5%'],
                'registered_date': '2021-09-12',
                'certificate_number': 'NG-GI-006'
            },
            'kano_groundnut': {
                'name': 'Kano Groundnut',
                'full_name': 'Kano Premium Groundnut',
                'region': 'Kano State',
                'state': 'kano',
                'description': 'High-quality groundnuts from Kano State, renowned for their oil content and flavor.',
                'status': 'pending',
                'characteristics': ['High oil content', 'Large kernel size', 'Sweet taste', 'Good storage'],
                'production_area': 'Kano State and surrounding areas',
                'traditional_knowledge': 'Traditional groundnut cultivation in Sudan savanna',
                'quality_standards': ['Oil content above 45%', 'Aflatoxin levels below 4ppb', 'No damaged kernels'],
                'registered_date': None,
                'certificate_number': None
            },
            'lagos_coconut': {
                'name': 'Lagos Coconut',
                'full_name': 'Lagos Coastal Coconut',
                'region': 'Lagos State',
                'state': 'lagos',
                'description': 'Coastal coconuts from Lagos lagoon areas, valued for their fresh water and meat quality.',
                'status': 'pending',
                'characteristics': ['Sweet coconut water', 'Tender meat', 'Large size', 'Coastal adaptation'],
                'production_area': 'Lagos coastal and lagoon areas',
                'traditional_knowledge': 'Traditional coastal coconut cultivation',
                'quality_standards': ['Minimum 300ml coconut water', 'No cracking', 'Fresh harvest'],
                'registered_date': None,
                'certificate_number': None
            }
        }
    
    def get_all_gis(self) -> List[Dict]:
        """Get all Nigerian GI products"""
        return list(self.nigerian_gis.values())
    
    def get_registered_gis(self) -> List[Dict]:
        """Get only registered GI products"""
        return [gi for gi in self.nigerian_gis.values() if gi['status'] == 'registered']
    
    def get_pending_gis(self) -> List[Dict]:
        """Get pending GI applications"""
        return [gi for gi in self.nigerian_gis.values() if gi['status'] == 'pending']
    
    def get_gi_by_name(self, name: str) -> Optional[Dict]:
        """Get GI information by name"""
        for gi_key, gi_data in self.nigerian_gis.items():
            if gi_data['name'].lower() == name.lower() or gi_data['full_name'].lower() == name.lower():
                return gi_data
        return None
    
    def get_gis_by_state(self, state: str) -> List[Dict]:
        """Get GI products by state"""
        return [gi for gi in self.nigerian_gis.values() if gi['state'] == state.lower()]
    
    def get_gi_choices_for_form(self, include_pending: bool = True) -> List[tuple]:
        """Get GI choices formatted for WTForms SelectField"""
        choices = [('', 'No GI Certification')]
        
        for gi_data in self.nigerian_gis.values():
            if gi_data['status'] == 'registered' or (include_pending and gi_data['status'] == 'pending'):
                choices.append((gi_data['name'], gi_data['full_name']))
        
        choices.append(('other', 'Other (Request New GI)'))
        return choices
    
    def search_gis(self, query: str) -> List[Dict]:
        """Search GI products by name, region, or characteristics"""
        query = query.lower()
        results = []
        
        for gi_data in self.nigerian_gis.values():
            # Search in name, region, description, and characteristics
            searchable_text = f"{gi_data['name']} {gi_data['region']} {gi_data['description']} {' '.join(gi_data['characteristics'])}".lower()
            if query in searchable_text:
                results.append(gi_data)
        
        return results
    
    def validate_gi_claim(self, produce_name: str, gi_label: str, farmer_state: str) -> Dict:
        """Validate a GI claim by a farmer"""
        validation_result = {
            'valid': False,
            'message': '',
            'suggestions': []
        }
        
        gi_info = self.get_gi_by_name(gi_label)
        
        if not gi_info:
            validation_result['message'] = f"GI '{gi_label}' is not recognized in the Nigerian GI registry."
            # Suggest similar GIs
            similar_gis = self.search_gis(gi_label)
            if similar_gis:
                validation_result['suggestions'] = [gi['name'] for gi in similar_gis[:3]]
            return validation_result
        
        # Check if farmer's state matches GI region
        if gi_info['state'] != farmer_state.lower():
            validation_result['message'] = f"GI '{gi_label}' is specific to {gi_info['region']}, but your location is {farmer_state.title()}."
            return validation_result
        
        # Check if produce name is compatible
        gi_produce_keywords = gi_info['name'].lower().split()
        produce_keywords = produce_name.lower().split()
        
        # Simple keyword matching
        if not any(keyword in produce_keywords for keyword in gi_produce_keywords):
            validation_result['message'] = f"Your produce '{produce_name}' doesn't match the GI product '{gi_info['name']}'."
            return validation_result
        
        # All checks passed
        validation_result['valid'] = True
        validation_result['message'] = f"GI claim for '{gi_label}' appears valid and will be reviewed by administrators."
        
        return validation_result
    
    def get_gi_statistics(self) -> Dict:
        """Get statistics about Nigerian GI products"""
        total_gis = len(self.nigerian_gis)
        registered = len(self.get_registered_gis())
        pending = len(self.get_pending_gis())
        
        # Count by states
        state_counts = {}
        for gi_data in self.nigerian_gis.values():
            state = gi_data['state']
            state_counts[state] = state_counts.get(state, 0) + 1
        
        return {
            'total_gis': total_gis,
            'registered': registered,
            'pending': pending,
            'by_state': state_counts
        }
    
    def get_gi_requirements(self) -> Dict:
        """Get general requirements for GI certification"""
        return {
            'documentation': [
                'Proof of traditional production methods',
                'Geographic boundary documentation',
                'Quality specifications and standards',
                'Evidence of reputation and distinctiveness',
                'Producer organization registration'
            ],
            'quality_standards': [
                'Product specifications must be clearly defined',
                'Quality control measures in place',
                'Traceability systems established',
                'Regular quality testing protocols'
            ],
            'geographic_link': [
                'Product must originate from specified geographic area',
                'Link between product quality and geographic origin',
                'Traditional production methods specific to the region',
                'Local environmental factors influence on product'
            ],
            'process': [
                'Submit initial application with supporting documents',
                'Technical review by experts',
                'Public consultation period',
                'Final assessment and decision',
                'Registration and certificate issuance'
            ]
        }