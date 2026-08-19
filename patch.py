import sys

target = '''        if onboard_btn:
            missing = [f for f, v in [("First Name", fname), ("Last Name", lname), ("Email", email)] if not v.strip()]
            if missing:
                st.warning(f"Please fill in: {', '.join(missing)}")
            elif dept_sel not in dept_map:
                st.warning("Select a valid department.")
            elif role_sel not in role_map:
                st.warning("Select a valid job role.")
            else:'''

replacement = '''        if onboard_btn:
            missing = [f for f, v in [("First Name", fname), ("Last Name", lname), ("Email", email), ("Education Field", edu_fld)] if not v.strip()]
            
            if missing:
                st.warning(f"Please fill in: {', '.join(missing)}")
            elif dept_sel not in dept_map:
                st.warning("Select a valid department.")
            elif role_sel not in role_map:
                st.warning("Select a valid job role.")
            elif "@" not in email or "." not in email:
                st.warning("Please enter a valid email address.")
            elif any(char.isdigit() for char in fname):
                st.warning("First name cannot contain numbers.")
            elif any(char.isdigit() for char in lname):
                st.warning("Last name cannot contain numbers.")
            elif yrs_co > tot_yrs:
                st.warning("Years at company cannot be greater than total working years.")
            elif yrs_role > yrs_co:
                st.warning("Years in current role cannot be greater than years at company.")
            elif (age - 16) < tot_yrs:
                st.warning(f"Total working years ({tot_yrs}) is logically too high for an employee of age {age}.")
            else:'''

with open('app/streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

if target in content:
    content = content.replace(target, replacement)
    with open('app/streamlit_app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS')
else:
    print('FAILED TO FIND TARGET')
