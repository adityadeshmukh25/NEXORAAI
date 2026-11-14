
import json

from pydantic import ValidationError

from app.schemas.architecture import ArchitecturePlanResult
from app.services.ollama_service import ollama_service


class ArchitecturePlanningAgent:

    async def generate_section(self, section_name, requirements, instructions):

        prompt = f"""
You are a senior software architect.

Analyze the following software requirements.

REQUIREMENTS:
{json.dumps(requirements, indent=2)}

TASK:
Generate ONLY the JSON object for this section:

{section_name}

INSTRUCTIONS:
{instructions}

Return valid JSON only.
Do not use Markdown.
Do not omit any requested fields.
Keep descriptions concise.
"""

        response = await ollama_service.generate_json(prompt)

        try:
            result = json.loads(response)

            if not isinstance(result, dict):
                raise ValueError("Expected a JSON object.")

            return result

        except json.JSONDecodeError as error:
            raise ValueError(
                f"Invalid JSON generated for {section_name}: {error}"
            )

    async def generate_architecture(self, requirement_analysis):

        requirement_data = requirement_analysis.analysis_result

        if isinstance(requirement_data, str):
            requirement_data = json.loads(requirement_data)

        if hasattr(requirement_data, "model_dump"):
            requirement_data = requirement_data.model_dump()

        try:

            # SECTION 1: Project overview and system architecture

            system = await self.generate_section(
                "project_overview and system_architecture",
                requirement_data,
                """
Return this exact structure:

{
  "project_overview": "Project overview",
  "system_architecture": {
    "architecture_style": "Layered Architecture",
    "description": "Architecture description",
    "components": [
      {
        "name": "Frontend",
        "description": "User interface",
        "technology": "React",
        "responsibilities": ["Display interface"]
      }
    ],
    "communication_flow": ["Frontend communicates with backend"]
  }
}

Include 4-5 practical components.
"""
            )

            # SECTION 2: Database design

            database = await self.generate_section(
                "database_design",
                requirement_data,
                """
Return this exact structure:

{
  "database_design": {
    "database_type": "PostgreSQL",
    "tables": [
      {
        "table_name": "users",
        "description": "User information",
        "fields": [
          {
            "name": "id",
            "data_type": "INTEGER",
            "constraints": ["PRIMARY KEY"]
          }
        ]
      }
    ],
    "relationships": ["One user can have multiple orders"]
  }
}

Include approximately 5 relevant tables.
"""
            )

            # SECTION 3: API design

            api = await self.generate_section(
                "api_design",
                requirement_data,
                """
Return this exact structure:

{
  "api_design": {
    "base_path": "/api",
    "endpoints": [
      {
        "method": "GET",
        "endpoint": "/products",
        "description": "Get all products",
        "request_body": null,
        "response": "List of products"
      }
    ]
  }
}

Include approximately 6 relevant REST API endpoints.
Every endpoint must have all five fields.
"""
            )

            # SECTION 4: Project directory structure

            structure = await self.generate_section(
                "project_structure",
                requirement_data,
                """
Return this exact structure:

{
  "project_structure": {
    "directories": [
      {
        "path": "backend/app/main.py",
        "description": "Backend entry point"
      }
    ]
  }
}

Include a practical frontend and backend folder structure.
Every directory entry must have path and description.
"""
            )

            # SECTION 5: Roadmap and recommendations

            planning = await self.generate_section(
                "technology_recommendations, development_roadmap, security_recommendations and scalability_recommendations",
                requirement_data,
                """
Return this exact structure:

{
  "technology_recommendations": [
    {
      "category": "Backend",
      "technology": "FastAPI",
      "reason": "Efficient API development"
    }
  ],
  "development_roadmap": [
    {
      "phase": 1,
      "title": "Backend Development",
      "tasks": ["Create API endpoints"],
      "estimated_effort": "3 days"
    }
  ],
  "security_recommendations": [
    "Use secure authentication"
  ],
  "scalability_recommendations": [
    "Optimize database queries"
  ]
}

Include:
- 3 technology recommendations.
- 4 development phases.
- 3 security recommendations.
- 3 scalability recommendations.
"""
            )

            # Combine all five sections

            complete_architecture = {
                "project_overview": system["project_overview"],
                "system_architecture": system["system_architecture"],
                "database_design": database["database_design"],
                "api_design": api["api_design"],
                "project_structure": structure["project_structure"],
                "technology_recommendations": planning[
                    "technology_recommendations"
                ],
                "development_roadmap": planning[
                    "development_roadmap"
                ],
                "security_recommendations": planning[
                    "security_recommendations"
                ],
                "scalability_recommendations": planning[
                    "scalability_recommendations"
                ]
            }

            # Validate the complete architecture

            validated = ArchitecturePlanResult.model_validate(
                complete_architecture
            )

            return validated

        except (KeyError, ValidationError) as error:
            raise ValueError(
                f"Architecture generation or validation failed: {error}"
            )


architecture_agent = ArchitecturePlanningAgent()
