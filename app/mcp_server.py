from mcp.server.fastmcp import FastMCP

mcp = FastMCP("study-guru-server")

@mcp.tool()
def search_study_materials(subject: str) -> str:
    """Search for relevant textbooks, articles, and study materials for a subject.
    
    Args:
        subject: The subject or topic to search for (e.g. Physics, Calculus, Biology).
    """
    subject_lower = subject.lower()
    if "physics" in subject_lower:
        return (
            "Found 2 books:\n"
            "1. 'University Physics' by Young and Freedman - Chapter 5 (Newtonian Mechanics)\n"
            "2. 'Feynman Lectures on Physics' Vol 1 - Mechanics and Gravity."
        )
    elif "calculus" in subject_lower or "math" in subject_lower:
        return (
            "Found 2 resources:\n"
            "1. MIT OpenCourseWare: Single Variable Calculus Lecture Notes\n"
            "2. 'Calculus' by Gilbert Strang - Chapter 3 (Derivatives and Integration)."
        )
    elif "biology" in subject_lower:
        return (
            "Found 1 resource:\n"
            "1. 'Campbell Biology' 12th Edition - Chapter 10 (Photosynthesis) and Chapter 8 (Metabolism)."
        )
    return f"Found 1 general resource: OpenStax introductory guide to {subject}."

@mcp.tool()
def get_topic_summary(topic: str) -> str:
    """Retrieve a comprehensive academic summary and key definitions for a specific topic.
    
    Args:
        topic: The academic topic name (e.g. Photosynthesis, Newtonian Mechanics).
    """
    topic_lower = topic.lower()
    if "photosynthesis" in topic_lower:
        return (
            "Summary of Photosynthesis:\n"
            "Photosynthesis is the process used by plants, algae, and certain bacteria to harness "
            "energy from sunlight and turn it into chemical energy.\n"
            "Key stages:\n"
            "- Light-dependent reactions (occurs in thylakoid membranes, produces ATP and NADPH)\n"
            "- Calvin Cycle (occurs in stroma, fixes CO2 into G3P/glucose)."
        )
    elif "mechanics" in topic_lower or "newton" in topic_lower:
        return (
            "Summary of Newtonian Mechanics:\n"
            "Classical mechanics describes the motion of macroscopic objects under the influence of forces.\n"
            "Newton's Three Laws of Motion:\n"
            "1. Law of Inertia: Object remains at rest or in uniform motion unless acted upon by force.\n"
            "2. F = ma: Force equals mass times acceleration.\n"
            "3. Action-Reaction: For every action, there is an equal and opposite reaction."
        )
    return f"Summary of {topic}: An academic overview covering the core theories, key definitions, and modern applications of {topic}."

@mcp.tool()
def generate_practice_questions(topic: str, difficulty: str = "medium") -> str:
    """Generate mock practice quiz questions for a topic.
    
    Args:
        topic: The topic to generate questions for.
        difficulty: The difficulty level (easy, medium, hard).
    """
    topic_lower = topic.lower()
    if "photosynthesis" in topic_lower:
        return (
            "Practice Quiz: Photosynthesis (Difficulty: " + difficulty + ")\n"
            "1. What pigment absorbs light energy in the chloroplasts? (Expected answer: Chlorophyll a)\n"
            "2. Where do the light-independent reactions (Calvin Cycle) take place? (Expected answer: Stroma)"
        )
    elif "mechanics" in topic_lower or "newton" in topic_lower:
        return (
            "Practice Quiz: Newtonian Mechanics (Difficulty: " + difficulty + ")\n"
            "1. What is the formula for weight? (Expected answer: W = mg)\n"
            "2. If net force is zero, what is the acceleration of the object? (Expected answer: Zero)"
        )
    return f"Practice Quiz: {topic} (Difficulty: {difficulty})\n1. Define the fundamental concepts of {topic}.\n2. Explain one major application of {topic}."

if __name__ == "__main__":
    mcp.run()
