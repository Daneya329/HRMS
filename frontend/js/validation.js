/*
 * Client-side validation - mirrors backend/validators.py (same limits, same messages).
 * Limits come from GET /api/rules so they can never drift from the server.
 * The server ALWAYS validates again; this only gives instant feedback.
 */
const Validation = (() => {
    function parseIso(value) {
        if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
        const [y, m, d] = value.split('-').map(Number);
        const dt = new Date(Date.UTC(y, m - 1, d));
        if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d) return null;
        return { y, m, d, iso: value };
    }

    function ageOn(birth, on) {
        let years = on.y - birth.y;
        if (on.m < birth.m || (on.m === birth.m && on.d < birth.d)) years -= 1;
        return years;
    }

    function addDays(iso, days) {
        const [y, m, d] = iso.split('-').map(Number);
        const dt = new Date(Date.UTC(y, m - 1, d + days));
        return dt.toISOString().slice(0, 10);
    }

    function parseTime(value) {
        if (!/^\d{2}:\d{2}$/.test(value || '')) return null;
        const [h, m] = value.split(':').map(Number);
        return h < 24 && m < 60 ? h * 60 + m : null;
    }

    const fmt = n => Number(n).toLocaleString('en-US');

    function checkName(errors, field, label, value, r) {
        if (!value) errors[field] = `${label} is required`;
        else if (value.length < r.nameMinLength) errors[field] = `${label} must be at least ${r.nameMinLength} characters`;
        else if (value.length > r.nameMaxLength) errors[field] = `${label} must be at most ${r.nameMaxLength} characters`;
        else if (!new RegExp(r.namePattern).test(value)) errors[field] = `${label} may only contain letters, spaces, apostrophes and hyphens`;
    }

    function employee(d, r, today) {
        const e = {};
        checkName(e, 'first_name', 'First name', d.first_name || '', r);
        checkName(e, 'last_name', 'Last name', d.last_name || '', r);

        const email = (d.email || '').toLowerCase();
        if (!email) e.email = 'Email is required';
        else if (email.length > 100) e.email = 'Email must be at most 100 characters';
        else if (!new RegExp(r.emailPattern).test(email) || email.includes('..')) e.email = 'Enter a valid email address, e.g. name@company.com';

        const phone = d.phone || '';
        const digits = phone.replace(/[\s-]/g, '');
        if (!phone) e.phone = 'Phone number is required';
        else if (!/^\+?\d+$/.test(digits)) e.phone = 'Phone number may only contain digits, spaces, dashes and a leading +';
        else {
            const n = digits.replace(/^\+/, '').length;
            if (n < r.phoneDigitsMin || n > r.phoneDigitsMax) e.phone = `Phone number must have ${r.phoneDigitsMin} to ${r.phoneDigitsMax} digits`;
        }

        if (!d.cnic) e.cnic = 'CNIC is required';
        else if (!new RegExp(r.cnicPattern).test(d.cnic)) e.cnic = 'CNIC must be in the format 12345-1234567-1';

        if (!r.genders.includes(d.gender)) e.gender = 'Please select a gender';

        const dob = parseIso(d.date_of_birth);
        const hire = parseIso(d.hire_date);
        if (!dob) e.date_of_birth = 'Enter a valid date of birth (YYYY-MM-DD)';
        else if (dob.iso >= today) e.date_of_birth = 'Date of birth must be in the past';
        else if (dob.y < 1900) e.date_of_birth = 'Date of birth is not realistic';

        if (!hire) e.hire_date = 'Enter a valid hire date (YYYY-MM-DD)';
        else if (hire.iso < r.companyFounded) e.hire_date = `Hire date cannot be before the company was founded (${r.companyFounded})`;
        else if (hire.iso > addDays(today, r.maxHireDaysAhead)) e.hire_date = `Hire date cannot be more than ${r.maxHireDaysAhead} days in the future`;

        if (dob && hire && !e.date_of_birth && !e.hire_date) {
            const age = ageOn(dob, hire);
            if (age < r.minAge) e.date_of_birth = `Employee must be at least ${r.minAge} years old on the hire date (would be ${age})`;
            else if (age > r.maxAge) e.date_of_birth = `Employee cannot be older than ${r.maxAge} on the hire date (would be ${age})`;
        }

        if (!d.department_id || !(Number(d.department_id) > 0)) e.department_id = 'Please select a department';

        const designation = d.designation || '';
        if (!designation) e.designation = 'Designation is required';
        else if (designation.length < r.designationMinLength || designation.length > r.designationMaxLength)
            e.designation = `Designation must be ${r.designationMinLength}-${r.designationMaxLength} characters`;

        if (!r.employmentTypes.includes(d.employment_type)) e.employment_type = 'Please select an employment type';

        const raw = String(d.salary ?? '').trim();
        if (!raw) e.salary = 'Salary is required';
        else if (!/^-?\d+(\.\d+)?$/.test(raw)) e.salary = 'Salary must be a number';
        else {
            const salary = Number(raw);
            const minimum = r.minWage[d.employment_type];
            if (/\.\d{3,}$/.test(raw)) e.salary = 'Salary may have at most 2 decimal places';
            else if (salary > r.maxSalary) e.salary = `Salary cannot exceed ${r.currency} ${fmt(r.maxSalary)}`;
            else if (minimum !== undefined && salary < minimum) e.salary = `Salary is below the minimum wage for ${d.employment_type} employees (${r.currency} ${fmt(minimum)})`;
            else if (salary <= 0) e.salary = 'Salary must be greater than zero';
        }

        if (d.status && !r.employeeStatuses.includes(d.status)) e.status = 'Status must be Active or Inactive';
        return e;
    }

    function department(d) {
        const e = {};
        const name = d.name || '';
        if (!name) e.name = 'Department name is required';
        else if (name.length < 2 || name.length > 50) e.name = 'Department name must be 2-50 characters';
        if ((d.description || '').length > 200) e.description = 'Description must be at most 200 characters';
        return e;
    }

    function attendance(d, r, today, hireDate) {
        const e = {};
        const day = parseIso(d.date);
        if (!day) e.date = 'Enter a valid date (YYYY-MM-DD)';
        else if (day.iso > today) e.date = 'Attendance cannot be marked for a future date';
        else if (hireDate && day.iso < hireDate) e.date = `Attendance cannot be before the hire date (${hireDate})`;

        const status = d.status || '';
        if (!r.attendanceStatuses.includes(status)) e.status = 'Please select a valid status';

        const rawIn = d.check_in || '', rawOut = d.check_out || '';
        const tin = rawIn ? parseTime(rawIn) : null;
        const tout = rawOut ? parseTime(rawOut) : null;
        if (rawIn && tin === null) e.check_in = 'Check-in must be a valid time (HH:MM)';
        if (rawOut && tout === null) e.check_out = 'Check-out must be a valid time (HH:MM)';
        const late = parseTime(r.lateAfter), earliest = parseTime(r.earliestCheckIn);

        if (status === 'Absent') {
            if (rawIn || rawOut) e.check_in = 'An absent employee cannot have check-in or check-out times';
        } else if (r.attendanceStatuses.includes(status) && !e.check_in) {
            if (tin === null) e.check_in = `Check-in time is required for status '${status}'`;
            else if (tin < earliest) e.check_in = `Check-in cannot be earlier than ${r.earliestCheckIn}`;
            else if (status === 'Present' && tin > late) e.status = `Check-in after ${r.lateAfter} must be marked as Late`;
            else if (status === 'Late' && tin <= late) e.status = `'Late' requires a check-in after ${r.lateAfter}`;
        }
        if (tin !== null && tout !== null && !e.check_out) {
            if (tout <= tin) e.check_out = 'Check-out must be later than check-in';
            else {
                const hours = Math.round((tout - tin) / 60 * 100) / 100;
                if (hours > r.maxWorkHours) e.check_out = `A shift cannot be longer than ${r.maxWorkHours} hours`;
                else if (status === 'Half Day' && hours > r.halfDayMaxHours) e.status = `A Half Day cannot exceed ${r.halfDayMaxHours} worked hours (${hours} h recorded)`;
            }
        }
        if (status === 'Half Day' && tin !== null && tout === null && !e.status) e.check_out = 'Check-out time is required for a Half Day';
        return e;
    }

    function leaveDays(start, end) {
        const a = parseIso(start), b = parseIso(end);
        if (!a || !b) return 0;
        return Math.round((Date.UTC(b.y, b.m - 1, b.d) - Date.UTC(a.y, a.m - 1, a.d)) / 86400000) + 1;
    }

    function leave(d, r, today, remaining) {
        const e = {};
        if (!(d.leave_type in r.leaveEntitlement)) e.leave_type = 'Please select a leave type';
        const start = parseIso(d.start_date), end = parseIso(d.end_date);
        if (!start) e.start_date = 'Enter a valid start date';
        else if (start.iso < today) e.start_date = 'Leave cannot start in the past';
        if (!end) e.end_date = 'Enter a valid end date';
        else if (start && end.iso < start.iso) e.end_date = 'End date cannot be before the start date';
        if (start && end && !e.start_date && !e.end_date) {
            const days = leaveDays(start.iso, end.iso);
            if (days > r.maxLeaveDaysPerRequest) e.end_date = `A single request cannot exceed ${r.maxLeaveDaysPerRequest} days`;
            else if (remaining !== undefined && remaining !== null && !e.leave_type && days > remaining)
                e.leave_type = `Not enough ${d.leave_type} leave: ${remaining} day(s) left this year, ${days} requested`;
        }
        const reason = d.reason || '';
        if (reason.length < r.reasonMinLength || reason.length > r.reasonMaxLength)
            e.reason = `Reason must be ${r.reasonMinLength}-${r.reasonMaxLength} characters`;
        return e;
    }

    function password(d) {
        const e = {};
        if (!d.current_password) e.current_password = 'Current password is required';
        const n = d.new_password || '';
        if (n.length < 8) e.new_password = 'New password must be at least 8 characters';
        else if (!/[A-Za-z]/.test(n) || !/\d/.test(n)) e.new_password = 'New password must contain a letter and a digit';
        if (n !== (d.confirm_password || '')) e.confirm_password = 'Passwords do not match';
        return e;
    }

    return { employee, department, attendance, leave, leaveDays, password, parseIso, ageOn, addDays };
})();
