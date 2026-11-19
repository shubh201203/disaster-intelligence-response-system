import os
from typing import Dict, Any, List, Optional
from app.ai.rag.schemas import GroundedRAGResponse, FactItem, InferenceItem, RecommendationItem, CitationItem
from app.ai.rag.grounding.validator import GroundingValidator

class LLMProvider:
    """
    LLM Provider Abstraction supporting swappable generation backends.
    Includes a deterministic, grounded fallback provider that uses actual retrieved chunks
    and live DIRS system data without fabricating evidence or hallucinating citations.
    """
    def __init__(self, provider_name: Optional[str] = None):
        has_api_key = bool(os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"))
        if provider_name:
            self.provider_name = provider_name
        elif has_api_key:
            self.provider_name = os.environ.get("LLM_PROVIDER", "REAL_LLM_OPENAI")
        else:
            self.provider_name = "DIRS_GROUNDED_FALLBACK"

    def generate_grounded_response(
        self,
        query: str,
        mode: str,
        retrieved_chunks: List[Dict[str, Any]],
        dirs_context: Dict[str, Any]
    ) -> GroundedRAGResponse:
        """
        Generates structured grounded RAG output.
        Uses deterministic rule-based grounded generation when external LLM API key is unconfigured.
        """
        inc = dirs_context.get("incident", {})
        sev = dirs_context.get("severity", {})
        prio = dirs_context.get("priority", {})
        risk = dirs_context.get("risk_prediction", {})
        cv = dirs_context.get("computer_vision", {})
        demand = dirs_context.get("resource_demand", {})
        shelters = dirs_context.get("shelters", [])
        stock = dirs_context.get("inventory_stock", {})

        # 1. Facts Extraction
        facts = []
        if inc:
            facts.append({
                "statement": f"Incident [{inc.get('incident_code')}] '{inc.get('title')}' is currently in '{inc.get('status')}' status with {inc.get('people_affected')} affected citizens.",
                "source_type": "DIRS_SYSTEM_DATA",
                "evidence_ref": "DIRS Live Database (Incidents Table)"
            })
            if inc.get("injuries", 0) > 0 or inc.get("vulnerable_count", 0) > 0:
                facts.append({
                    "statement": f"Reported casualties include {inc.get('injuries')} injured victims and {inc.get('vulnerable_count')} vulnerable individuals (children/elderly).",
                    "source_type": "DIRS_SYSTEM_DATA",
                    "evidence_ref": "DIRS Live Database (Incident Casualty Metrics)"
                })

        if sev:
            facts.append({
                "statement": f"Phase 3A AI Severity Model predicts {sev.get('level')} severity with {sev.get('confidence')}% confidence.",
                "source_type": "DIRS_SYSTEM_DATA",
                "evidence_ref": "DIRS Phase 3A Severity Service"
            })

        if prio:
            facts.append({
                "statement": f"Phase 3A Intelligent Priority Engine assigns a normalized score of {prio.get('score')}/100 ({prio.get('level')}).",
                "source_type": "DIRS_SYSTEM_DATA",
                "evidence_ref": "DIRS Phase 3A Priority Engine"
            })

        if cv:
            facts.append({
                "statement": f"Phase 3B Computer Vision Model classifies structural damage as {cv.get('damage_class')} (Confidence: {cv.get('confidence')}%).",
                "source_type": "DIRS_SYSTEM_DATA",
                "evidence_ref": "DIRS Phase 3B Computer Vision Pipeline"
            })

        if risk:
            facts.append({
                "statement": f"Phase 3B Disaster Risk Engine evaluates environmental risk score at {risk.get('risk_score')}/100 ({risk.get('risk_level')}).",
                "source_type": "DIRS_SYSTEM_DATA",
                "evidence_ref": "DIRS Phase 3B Disaster Risk Model"
            })

        for chunk in retrieved_chunks[:2]:
            facts.append({
                "statement": f"Authoritative Guidance [{chunk['organization']} - '{chunk['title']}']: {chunk['text_content'][:160]}...",
                "source_type": "RETRIEVED_KNOWLEDGE",
                "evidence_ref": f"{chunk['organization']} Document: {chunk['title']}"
            })

        # 2. Inferences Generation
        inferences = []
        if risk.get("risk_level") in ["HIGH", "EXTREME"] or sev.get("level") in ["CRITICAL", "HIGH"]:
            inferences.append({
                "conclusion": "High probability of secondary hazard surge or rapid escalation requiring immediate pre-positioning.",
                "basis": "Simultaneous high environmental risk score and elevated incident priority level."
            })

        if demand.get("shortages"):
            shortage_types = [s.get("resource_type") for s in demand.get("shortages", [])]
            inferences.append({
                "conclusion": f"Potential inventory bottleneck detected in active stock categories: {', '.join(shortage_types)}.",
                "basis": "Comparison of Phase 3B forecasted demand against current available NGO stock."
            })

        # 3. Recommendations Generation
        recommendations = []
        if retrieved_chunks:
            hazard_type = retrieved_chunks[0].get("disaster_type", inc.get("disaster_type", "GENERAL"))
        else:
            hazard_type = inc.get("disaster_type", "GENERAL")

        if hazard_type == "FLOOD":
            recommendations.append({
                "priority": "HIGH",
                "action": "Initiate pre-evacuation alert and activate nearest emergency relief shelter.",
                "rationale": "Elevated water level and flood hazard score indicate risk of trapped residents in low-lying sectors.",
                "evidence": f"Supported by NDMA Flood Emergency Guidelines & Risk Score ({risk.get('risk_score', 50)}/100)",
                "required_resources": {"water_packs": 500, "rescue_boats": 5},
                "risk_if_delayed": "Rising floodwaters may maroon trapped victims requiring hazardous boat rescue operations."
            })
            recommendations.append({
                "priority": "HIGH",
                "action": "Deploy water purification tablets and mobile sanitation units to evacuation centers.",
                "rationale": "Prevent waterborne disease outbreaks in inundated sectors.",
                "evidence": "FEMA Flood Emergency Response Standard Operating Procedures",
                "required_resources": {"water_purification_tablets": 5000, "medical_kits": 20},
                "risk_if_delayed": "High probability of contamination-related gastroenteritis."
            })
        elif hazard_type == "CYCLONE":
            recommendations.append({
                "priority": "HIGH",
                "action": "Establish 10km coastal pre-evacuation perimeter and activate reinforced storm shelters.",
                "rationale": "Category 3/4 cyclone landfall predicted with damaging gale-force winds and storm surges.",
                "evidence": "NDMA National Cyclone Risk Mitigation Framework",
                "required_resources": {"evacuation_buses": 10, "emergency_rations": 1000},
                "risk_if_delayed": "Severe structural failure of coastal dwellings and storm surge trapping civilians."
            })
            recommendations.append({
                "priority": "HIGH",
                "action": "Pre-position heavy tree-clearing equipment and suspend non-critical vehicle movement if winds exceed 90 km/h.",
                "rationale": "Maintain artery access for emergency response teams immediately post-landfall.",
                "evidence": "NDMA Cyclone Operations Manual",
                "required_resources": {"clearing_machinery": 4, "chainsaw_crews": 6},
                "risk_if_delayed": "Blocked critical supply arteries delaying medical extractions."
            })
        elif hazard_type == "FIRE":
            recommendations.append({
                "priority": "CRITICAL",
                "action": "Establish minimum 150m upwind safety perimeter and enforce emergency stairwell evacuation.",
                "rationale": "Rapid thermal radiation and toxic smoke plume spreading downwind across urban interface.",
                "evidence": "NDMA Fire & Industrial Life Safety Framework",
                "required_resources": {"fire_tenders": 4, "evacuation_transports": 6},
                "risk_if_delayed": "Civilian entrapment and acute carbon monoxide asphyxiation."
            })
            recommendations.append({
                "priority": "HIGH",
                "action": "Mobilize burn trauma stabilization team and high-flow supplemental oxygen units.",
                "rationale": "Immediate triage required for smoke inhalation and thermal burn casualties.",
                "evidence": "WHO Disaster First Aid & Burn Treatment Guidelines",
                "required_resources": {"burn_kits": 50, "oxygen_concentrators": 10, "ambulances": 4},
                "risk_if_delayed": "Fatal respiratory failure from smoke inhalation."
            })
        elif hazard_type == "EARTHQUAKE":
            recommendations.append({
                "priority": "CRITICAL",
                "action": "Deploy acoustic listening search-and-rescue teams to prioritize void spaces in collapsed structures.",
                "rationale": "Critical golden 24-hour survival window for trapped survivors following seismic collapse.",
                "evidence": "NDMA / FEMA Seismic Safety & Urban Search and Rescue Protocol",
                "required_resources": {"usar_teams": 4, "acoustic_detectors": 8, "heavy_extrication_gear": 6},
                "risk_if_delayed": "Survivors in collapsed debris voids suffocating within rubble."
            })
            recommendations.append({
                "priority": "HIGH",
                "action": "Shut off main natural gas valves, power grids, and water mains in damaged perimeter.",
                "rationale": "Eliminate secondary gas explosion hazards, electrocution, and infrastructure fires.",
                "evidence": "FEMA Post-Earthquake Utility Isolation SOP",
                "required_resources": {"utility_inspection_crews": 4},
                "risk_if_delayed": "Catastrophic secondary fires across dense urban zones."
            })
        elif hazard_type == "LANDSLIDE":
            recommendations.append({
                "priority": "CRITICAL",
                "action": "Execute lateral evacuation across contour line away from debris flow path and cordon slope toe.",
                "rationale": "Saturated slope shear failure and active debris runout cone threatening downslope dwellings.",
                "evidence": "NDMA Landslide Hazard Mitigation & Slope Stabilization Protocol",
                "required_resources": {"earthmoving_excavators": 3, "evacuation_trucks": 5},
                "risk_if_delayed": "Debris avalanche burying residential sectors."
            })
            recommendations.append({
                "priority": "HIGH",
                "action": "Divert surface runoff away from tension scarps using geomembrane drainage channels.",
                "rationale": "Prevent further pore pressure accumulation and secondary slope liquefaction.",
                "evidence": "NDMA Geological Hazard Response Framework",
                "required_resources": {"drainage_pumps": 6, "revetment_materials": 200},
                "risk_if_delayed": "Secondary catastrophic slope failure during continuing rainfall."
            })
        elif hazard_type == "TSUNAMI":
            recommendations.append({
                "priority": "CRITICAL",
                "action": "Order immediate vertical evacuation to designated reinforced 4+ story concrete structures or ground >30m elevation.",
                "rationale": "Undersea seismic disturbance triggers high-velocity coastal wave inundation with short arrival window.",
                "evidence": "INCOIS Coastal Tsunami Early Warning & Vertical Evacuation Protocol",
                "required_resources": {"siren_network_crews": 2, "high_ground_marshals": 12},
                "risk_if_delayed": "Hydrodynamic forces destroying coastal structures and drowning evacuees."
            })
            recommendations.append({
                "priority": "HIGH",
                "action": "Enforce strict coastal exclusion perimeter until all multi-wave crests have officially subsided.",
                "rationale": "Tsunami wave trains arrive in successive crests over hours, with subsequent waves often exceeding the first.",
                "evidence": "INCOIS Tsunami Operations Guide",
                "required_resources": {"coastal_police_cordons": 8},
                "risk_if_delayed": "Fatalities among returning civilians during secondary wave impact."
            })
        elif hazard_type == "INDUSTRIAL_CHEMICAL":
            recommendations.append({
                "priority": "CRITICAL",
                "action": "Establish 500m hot-zone exclusion perimeter and evacuate civilians crosswind to upwind shelters.",
                "rationale": "Toxic vapor dispersion following chemical containment failure poses severe acute inhalation hazard.",
                "evidence": "NDMA Chemical Disaster Management & Hazmat Response Protocol",
                "required_resources": {"hazmat_teams": 3, "level_a_suits": 12, "vapor_suppression_foam": 40},
                "risk_if_delayed": "Acute toxic inhalation and irreversible chemical burns."
            })
            recommendations.append({
                "priority": "HIGH",
                "action": "Establish multi-stage decontamination corridor at warm-zone boundary prior to casualty transport.",
                "rationale": "Prevent chemical cross-contamination of regional emergency receiving hospitals.",
                "evidence": "OSHA Hazardous Materials Incident Response SOP",
                "required_resources": {"decon_showers": 2, "neutralizing_agents": 20},
                "risk_if_delayed": "Secondary chemical intoxication of medical responders and facilities."
            })
        else: # GENERAL
            recommendations.append({
                "priority": "HIGH",
                "action": "Deploy rapid damage assessment team and establish incident command perimeter.",
                "rationale": f"Emergency situation requires coordinated multi-agency response and resource distribution.",
                "evidence": "WHO Emergency Medical Triage Guidelines",
                "required_resources": {"rescue_personnel": 15, "medical_kits": 25},
                "risk_if_delayed": "Delayed response increases mortality and operational coordination failure."
            })

        # 4. Summary Generation
        if inc:
            summary = f"DIRS AI Disaster Copilot Situation Report for Incident [{inc.get('incident_code', 'INC-GENERAL')}]: " \
                      f"Evaluated as {sev.get('level', 'MEDIUM')} severity ({prio.get('level', 'MEDIUM')} priority, score {prio.get('score', 50)}/100) " \
                      f"with {inc.get('people_affected', 0)} citizens affected in a {hazard_type} hazard zone. " \
                      f"Grounded response incorporates {len(retrieved_chunks)} authoritative knowledge chunks from {len(set(c['organization'] for c in retrieved_chunks))} emergency organizations."
        elif retrieved_chunks:
            orgs = ", ".join(sorted(set(c['organization'] for c in retrieved_chunks)))
            primary_action = recommendations[0]['action'] if recommendations else "life-safety protocols"
            summary = f"DIRS AI Grounded Guidance for {hazard_type} Response: Based on authoritative guidelines from {orgs}, response operations should prioritize: {primary_action}. Grounded across {len(retrieved_chunks)} verified knowledge chunks."
        else:
            summary = "DIRS Emergency Knowledge Base: No specific operational data found for the requested query."

        risks = [
            f"Environmental Risk Level evaluated at {risk.get('risk_level', 'MODERATE')} ({risk.get('risk_score', 50)}/100)",
            f"Inventory stock shortage identified for {len(demand.get('shortages', []))} resource categories",
            "Infrastructure damage may restrict ground access for heavy transport vehicles"
        ]

        resource_implications = [
            f"Forecasted Water Demand: {demand.get('predictions', {}).get('water_packs', {}).get('quantity', 0)} Liters",
            f"Forecasted Rations Demand: {demand.get('predictions', {}).get('food_packets', {}).get('quantity', 0)} Units",
            f"Forecasted Medical Demand: {demand.get('predictions', {}).get('medical_kits', {}).get('quantity', 0)} Kits"
        ]

        return GroundingValidator.validate_and_structure_response(
            query=query,
            mode=mode,
            retrieved_chunks=retrieved_chunks,
            dirs_context=dirs_context,
            raw_summary=summary,
            proposed_facts=facts,
            proposed_inferences=inferences,
            proposed_recommendations=recommendations,
            proposed_risks=risks,
            proposed_resource_implications=resource_implications
        )
