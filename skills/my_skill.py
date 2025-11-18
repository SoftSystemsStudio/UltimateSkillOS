from skill_engine.base import BaseSkill
from pydantic import BaseModel
from skill_engine.domain import SkillInput, SkillOutput

class MySkillInput(BaseModel):
    text: str = ""

class MySkillOutput(BaseModel):
    message: str
    params: dict

class MySkill(BaseSkill):
    name = "my_skill"
    version = "1.0.0"
    description = "A demonstration skill for modularity testing."
    input_schema = MySkillInput
    output_schema = MySkillOutput
    sla = None

    def invoke(self, input_data: SkillInput, context) -> SkillOutput:
        params = input_data.payload
        return {"message": "MySkill executed!", "params": params}
