
# Service - rewiring the rejected taskss
def rewire_tasks_with_remarks(eo: str, remarks: str, tasks:dict)-> dict:
 """

    Returns
    -------
    Dict
        A JSON-serializable dictionary in the shape:
        {
          "tasks": [
            {
              "id": int,
              "title": str,
              "description": str,
              "category_dept": str,
              "assignee": "",                 # intentionally empty at this stage
              "status": "Pending",
              "due_date": "YYYY-MM-DD"|"TBD",
              "created_at": "ISO-8601"
            },
            ...
          ],
          "summary": "tasks are changed in such a way....." # overview of what has been changed w.r.t the remarks
        }
    """
 


def generate_task_update_from_update_email(employee_role, raw_update, task)-> Dict:
    """
     Returns
    -------
    Dict , Task_Update: It is basically a structered format describing progess of a single Task 

        {
            *   progress_pct (int)
            •	hours_spent (numeric)
            •	status_note (text)
            •	blockers (jsonb)
            •	risks (jsonb)
            •	next_actions (jsonb)
            •	extraction_confidence (numeric)
            •	created_at
        }
    """

list: Task_updates()

def generate_summaru_from_list_of_task_updates(task_update_list: list, EO): # to be sent to PMO
   """
   It should generate a summary of tasks updates from all the employees in the context of EO. 
   Which can help the PMO understand the progress of a single EO.

   one single table

   return type:
   TBD (to be decided), EO_progress: It is basically a structered format describing progess of a single Executive Order (EO)

   """

list: EO_progress()
def generate_summary_of_multiple_EOs(EO_progresses: list(EO_progress)): #CFO
    """
   I
   """
