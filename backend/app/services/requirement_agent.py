
import json

from pydantic import ValidationError

from app.schemas.requirements import RequirementAnalysisResult
from app.services.ollama_service import ollama_service


class RequirementAnalysisAgent:

    SYSTEM_PROMPT = """
You are an expert Senior Software Architect and
Business Analyst.

Your job is to analyze software project requirements
and convert them into a structured requirement document.

Analyze the user's software idea carefully.

Return ONLY valid JSON.

Follow this exact JSON structure:

{
    "project_summary": "Brief project description",

    "functional_requirements": [
        {
            "id": "FR-001",
            "title": "Requirement title",
            "description": "Detailed description",
            "priority": "High"
        }
    ],

    "non_functional_requirements": [
        {
            "category": "Performance",
            "description": "Requirement description"
        }
    ],

    "suggested_modules": [
        {
            "name": "Module name",
            "description": "Module purpose"
        }
    ],

    "assumptions": [
        "Assumption"
    ],

    "clarification_questions": [
        "Question"
    ],

    "acceptance_criteria": [
        "Acceptance criterion"
    ],

    "suggested_technology_stack": [
        "Technology"
    ],

    "out_of_scope": [
        "Feature excluded from current scope"
    ]
}

IMPORTANT RULES:

1. Identify all major functional requirements.
2. Assign unique IDs such as FR-001, FR-002.
3. Priority must be High, Medium or Low.
4. Identify security, scalability and performance needs.
5. Suggest logical software modules.
6. Do not invent business requirements as confirmed facts.
7. Put uncertain details in assumptions or clarification questions.
8. Keep recommendations practical.
9. Do not generate application source code.
10. If information is missing, clearly identify it.
11. Keep the response concise.
12. Generate approximately 5-8 functional requirements.
13. Generate approximately 4-6 non-functional requirements.
14. Suggest approximately 4-6 modules.
15. Keep descriptions to 1-2 sentences.
16. Limit clarification questions to 5.
17. Return complete valid JSON without Markdown.
"""

    async def analyze(self, requirements: str):

        prompt = f"""
{self.SYSTEM_PROMPT}

USER SOFTWARE REQUIREMENTS:

{requirements}

Analyze these requirements and return the JSON document.
"""

        response = await ollama_service.generate_json(prompt)

        try:
            result = json.loads(response)

            validated_result = RequirementAnalysisResult.model_validate(
                result
            )

            return validated_result

        except json.JSONDecodeError:
            raise ValueError(
                "The AI returned invalid JSON. Please try again."
            )

        except ValidationError as error:
            raise ValueError(
                f"The AI response did not match the required structure: {error}"
            )


requirement_agent = RequirementAnalysisAgent()
