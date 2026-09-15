Link to Code Repository: https://github.com/RuiHan-SIT/26INF1103P5-2

1. Problem Statement and Target Users

Problem Statement:
When an employee resigns, goes on temporary reassignment, or takes extended leave, they may need to prepare a handover document for the person taking over their responsibilities. However, handovers are often written in templates or unstructured notes, which may cause important information such as outstanding tasks, deadlines, responsible persons, dependencies, or relevant resources to be missed or unclear.

Target Users:
Employees preparing work handovers and colleagues taking over their tasks and responsibilities.

2. User Inputs
-   The user provides a handover document containing information about their completed and outstanding work.
-   The handover may be entered as free-form text or loaded from a file.

3. Usage of AI
-	Extract completed and outstanding tasks.
-	Extract the responsible person(s) and deadline for each outstanding task.
-	Assign each outstanding task a High, Medium or Low priority based mainly on its deadline and context.
-	Identify information that is missing or unclear.
-	Produce a structured summary.


4. Business Rules
    -	User Input Validation:
        a.  Meets minimum input length and use a supported file size/format.
        b.	Ensure file is not empty or corrupted and encoded properly.
        c.	Detect sensitive personal identifiers such as NRIC/passport numbers and require users to remove them before file is sent to AI.
    
    -   Handover Rules:
        a.	Each outstanding task must have at least one “Task Owner” and a “Deadline”, or the handover is marked as “Needs Clarification”.
        b.	If all requirements are met, mark as “Ready for Handover”.
        c.	Format date and time values (e.g. Deadline).
        d.	Sort outstanding tasks using AI-assigned “Priority” (High  Medium  Low)
    
    -   Output Validation:
        a.	Ensure AI returns a properly formatted JSON response. 
        b.	Ensure the LLM did not invent new tasking and responsibility.
