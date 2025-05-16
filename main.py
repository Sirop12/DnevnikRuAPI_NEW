from dnevnik_formatter import DnevnikFormatter
from datetime import datetime
formatter = DnevnikFormatter(token="token")
STUDY_YEAR = 2024
QUARTER = 3
subject_id = 630640156086198  


subject_ranking = formatter.get_subject_ranking(STUDY_YEAR, QUARTER, subject_id)



print(f"\nРейтинг по предмету (ID={subject_id}):")
for i, student in enumerate(subject_ranking, 1):
    print(f"{i}. {student['name']}: {student['avg_grade']} (оценок: {student['marks_count']})")
