"""
Example: How to use the new memory system in skills.

Shows the recommended patterns for memory access in the new architecture.
"""

from skill_engine.domain import SkillInput, SkillOutput
from skill_engine.memory import MemoryRecord
from skill_engine.skill_base import RunContext


# ============================================================================
# EXAMPLE 1: Simple skill using memory
# ============================================================================


class ResearchSkillWithMemory:
    """Example skill that uses memory via RunContext."""

    name = "research"
    version = "1.2.0"

    def invoke(self, input_data: SkillInput, context: RunContext) -> SkillOutput:
        """
        Research skill that:
        1. Recalls relevant memory for context
        2. Performs research
        3. Stores findings in long-term memory
        """
        # Get memory facade from context
        memory = context.memory

        # Recall relevant context
        query = input_data.payload.get("query", "")
        context_str = memory.recall_context(query, top_k=3)

        # Do research (simulated)
        findings = f"Research results for: {query}"

        # Store findings in long-term memory for future reference
        memory.add(
            content=findings,
            tier="long_term",
            metadata={"source": "research", "query": query},
        )

        # Store brief note in scratchpad for this step
        memory.add(
            content=f"Researched: {query}",
            tier="scratchpad",
            metadata={"tag": "step_log"},
        )

        return SkillOutput(
            payload={
                "findings": findings,
                "context_used": context_str,
            },
            metrics={"search_time_ms": 125.0},
        )


# ============================================================================
# EXAMPLE 2: Planner/Reflection using scratchpad
# ============================================================================


class PlannerWithScratchpad:
    """Example planner that uses scratchpad for working memory."""

    name = "planner"
    version = "1.1.0"

    def invoke(self, input_data: SkillInput, context: RunContext) -> SkillOutput:
        """
        Planner that:
        1. Uses scratchpad for intermediate reasoning
        2. Records plan steps
        3. Stores final plan in long-term memory
        """
        memory = context.memory
        goal = input_data.payload.get("goal", "")

        # Use scratchpad for working memory during planning
        memory.scratchpad.add_note("goal", goal)
        memory.scratchpad.add_note("step_count", 0)

        # Generate steps
        steps = [
            {"id": "step_1", "description": "Gather information"},
            {"id": "step_2", "description": "Analyze"},
            {"id": "step_3", "description": "Conclude"},
        ]

        # Update scratchpad with plan
        memory.scratchpad.add_note("steps", steps)
        memory.scratchpad.add_note("step_count", len(steps))

        # Log to scratchpad memory for debugging
        memory.add(
            content=f"Generated {len(steps)} steps for goal: {goal}",
            tier="scratchpad",
            metadata={"tag": "planning"},
        )

        # Store plan in long-term memory for learning
        plan_summary = f"Plan for '{goal}': {len(steps)} steps"
        memory.add(
            content=plan_summary,
            tier="long_term",
            metadata={"type": "plan", "goal": goal},
        )

        return SkillOutput(
            payload={"plan": steps, "step_count": len(steps)},
        )


# ============================================================================
# EXAMPLE 3: Memory migration across tiers
# ============================================================================


def migrate_short_to_long_term(context: RunContext, query: str):
    """
    Example of migrating important findings from short-term to long-term.

    This would typically be done by the agent or a reflection step.
    """
    memory = context.memory

    # Search short-term memory
    short_term_results = memory.search(query, tier="short_term", top_k=3)

    # Migrate important results to long-term
    for record in short_term_results:
        if "important" in record.metadata or record.content:
            # Re-add to long-term with preserved metadata
            memory.add(
                content=record.content,
                tier="long_term",
                metadata={**record.metadata, "source": "migrated_from_short_term"},
            )


# ============================================================================
# EXAMPLE 4: Testing skills with isolated memory
# ============================================================================


def test_skill_with_memory():
    """Example of testing a skill with isolated memory."""
    from skill_engine.memory import (
        MemoryFacade,
        MemoryManager,
        ShortTermMemory,
        LongTermMemory,
        Scratchpad,
        InMemoryBackend,
    )
    import uuid

    # Create isolated memory for the test
    memory_manager = MemoryManager(long_term_backend=InMemoryBackend())
    memory_facade = memory_manager.get_facade()

    # Create test context
    context = RunContext(
        trace_id=str(uuid.uuid4()),
        correlation_id=str(uuid.uuid4()),
        memory_facade=memory_facade,
    )

    # Run skill with isolated memory
    skill = ResearchSkillWithMemory()
    input_data = SkillInput(
        payload={"query": "what is AI?"},
        trace_id=context.trace_id,
        correlation_id=context.correlation_id,
    )

    output = skill.invoke(input_data, context)

    # Assert memory operations
    assert memory_facade.stats()["long_term"] > 0
    assert memory_facade.stats()["scratchpad"] > 0

    print("✓ Skill memory test passed")
    print(f"Memory stats: {memory_facade.stats()}")


if __name__ == "__main__":
    test_skill_with_memory()
