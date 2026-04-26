from __future__ import annotations

import random
from datetime import date, timedelta

import pandas as pd


def generate_hr_dataset(size: int = 240, seed: int = 42) -> pd.DataFrame:
    random.seed(seed)
    departments = ["Sales", "Operations", "Finance", "IT", "HR", "Customer Care"]
    job_families = ["Manager", "Specialist", "Senior Specialist", "Coordinator", "Analyst"]
    cities = ["Riyadh", "Jeddah", "Dammam", "Khobar"]
    insurance_levels = ["A", "B", "C"]

    rows: list[dict] = []
    today = date.today()

    for idx in range(1, size + 1):
        is_saudi = random.random() < 0.62
        base_salary = random.randint(5000, 42000)
        salary = base_salary + random.randint(0, 2500)
        insurance_cost = int(salary * random.uniform(0.08, 0.13))
        iqama_days = random.randint(-30, 365) if not is_saudi else None
        contract_days = random.randint(-45, 420)
        performance = round(random.uniform(2.1, 5.0), 2)
        age = random.randint(22, 58)
        tenure = round(random.uniform(0.4, 18.0), 1)

        rows.append(
            {
                "employee_id": f"LV-{idx:04d}",
                "employee_name": f"Employee {idx:03d}",
                "is_saudi": is_saudi,
                "nationality": "Saudi" if is_saudi else random.choice(["Indian", "Egyptian", "Jordanian", "Pakistani"]),
                "department": random.choice(departments),
                "job_family": random.choice(job_families),
                "city": random.choice(cities),
                "gender": random.choice(["Male", "Female"]),
                "insurance_level": random.choice(insurance_levels),
                "salary": salary,
                "insurance_cost": insurance_cost,
                "iqama_expiry_date": (today + timedelta(days=iqama_days)).isoformat() if iqama_days is not None else None,
                "iqama_days_remaining": iqama_days,
                "contract_end_date": (today + timedelta(days=contract_days)).isoformat(),
                "contract_days_remaining": contract_days,
                "performance_score": performance,
                "age": age,
                "tenure_years": tenure,
            }
        )

    return pd.DataFrame(rows)
