const API = '';
const TERM_COUNT = 4;

const STATUS_LABELS = {
    draft: 'Draft',
    pending: 'Pending review',
    approved: 'Approved',
    rejected: 'Rejected',
    changes_requested: 'Changes requested',
};

const CREDIT_TARGET = 30;
const CREDIT_MIN = 27;
const CREDIT_MAX = 33;
const TOTAL_CREDITS = 120;

let currentUser = null;
let courses = [];
let showRegister = false;

function statusLabel(status) {
    return STATUS_LABELS[status] || status;
}

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function formatUserName(user) {
    if (!user) return '';
    if (user.first_name && user.last_name) {
        return `${user.first_name} ${user.last_name}`;
    }
    if (user.first_name) return user.first_name;
    if (user.name) return user.name;
    return user.email || '';
}

function getToken() {
    const token = localStorage.getItem('token');
    return token ? token.trim() : null;
}

function setToken(token) {
    localStorage.setItem('token', token);
}

function clearToken() {
    localStorage.removeItem('token');
}

async function api(path, options = {}) {
    const token = getToken();
    const headers = { ...(options.headers || {}) };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const isJsonBody = options.body && typeof options.body === 'object' && !(options.body instanceof FormData);
    if (isJsonBody) {
        headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(`${API}${path}`, {
        ...options,
        headers,
        body: isJsonBody ? JSON.stringify(options.body) : options.body,
    });

    if (res.status === 401) {
        clearToken();
        renderLogin();
        throw new Error('Session expired. Please sign in again.');
    }

    if (!res.ok) {
        let message = 'Request failed';
        try {
            const err = await res.json();
            message = err.detail || JSON.stringify(err);
        } catch {
            message = await res.text().catch(() => `HTTP ${res.status}`);
        }
        throw new Error(message);
    }

    return res.status === 204 ? null : res.json();
}

async function renderUserAdmin() {
    const users = await api('/auth/users');
    const rows = users.map(u => `
        <tr>
            <td>${escapeHtml(formatUserName(u))}</td>
            <td>${escapeHtml(u.email)}</td>
            <td>${escapeHtml(u.role)}</td>
            <td>${u.is_active ? 'Active' : 'Closed'}</td>
            <td>
                ${u.role === 'student' ? `<button class="danger" onclick="closeAccount(${u.id})">Close</button>` : ''}
            </td>
        </tr>
    `).join('');

    document.getElementById('main').innerHTML = `
        <div class="card">
            <h2>Account Management</h2>
            <h3>Create Account</h3>
            <div class="form-row">
                <input id="new-user-email" type="email" placeholder="Email">
                <input id="new-user-password" type="password" placeholder="Password">
                <input id="new-user-first-name" type="text" placeholder="First name">
                <input id="new-user-last-name" type="text" placeholder="Last name">
                <select id="new-user-role">
                    <option value="student">Student</option>
                    <option value="director">Director</option>
                </select>
                <input id="new-user-admission-term" type="text" placeholder="Admission term (optional)">
                <input id="new-user-secret" type="password" placeholder="Director secret">
                <button onclick="createUser()">Create</button>
            </div>
            <h3>All Accounts</h3>
            <table>
                <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr></thead>
                <tbody>${rows || '<tr><td colspan="5">No accounts.</td></tr>'}</tbody>
            </table>
            <div class="actions">
                <button class="secondary" onclick="renderApp()">Back</button>
            </div>
        </div>
    `;
}

async function renderAccountAdminInline() {
    const container = document.getElementById('account-admin-container');
    if (!container) return;
    const users = await api('/auth/users');
    const rows = users.map(u => `
        <tr>
            <td>${escapeHtml(formatUserName(u))}</td>
            <td>${escapeHtml(u.email)}</td>
            <td>${escapeHtml(u.role)}</td>
            <td>${u.is_active ? 'Active' : 'Closed'}</td>
            <td>
                ${u.role === 'student' ? `<button class="danger" onclick="closeAccount(${u.id})">Close</button>` : ''}
            </td>
        </tr>
    `).join('');

    container.innerHTML = `
        <h3>Create Account</h3>
        <div class="form-row">
            <input id="new-user-email" type="email" placeholder="Email">
            <input id="new-user-password" type="password" placeholder="Password">
            <input id="new-user-first-name" type="text" placeholder="First name">
            <input id="new-user-last-name" type="text" placeholder="Last name">
            <select id="new-user-role">
                <option value="student">Student</option>
                <option value="director">Director</option>
            </select>
            <input id="new-user-admission-term" type="text" placeholder="Admission term (optional)">
            <input id="new-user-secret" type="password" placeholder="Director secret">
            <button onclick="createUser()">Create</button>
        </div>
        <h3 style="margin-top:1.5rem">All Accounts</h3>
        <table>
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>${rows || '<tr><td colspan="5">No accounts.</td></tr>'}</tbody>
        </table>
    `;
}

async function createUser() {
    const email = document.getElementById('new-user-email').value.trim();
    const password = document.getElementById('new-user-password').value;
    const first_name = document.getElementById('new-user-first-name').value.trim();
    const last_name = document.getElementById('new-user-last-name').value.trim();
    const role = document.getElementById('new-user-role').value;
    const admission_term = document.getElementById('new-user-admission-term').value.trim();
    const director_secret = document.getElementById('new-user-secret').value;

    try {
        await api('/auth/director/users', {
            method: 'POST',
            body: { email, password, first_name, last_name, role, admission_term, director_secret }
        });
        if (document.getElementById('account-admin-container')) {
            renderAccountAdminInline();
        } else {
            renderUserAdmin();
        }
    } catch (e) {
        alert(e.message);
    }
}

async function closeAccount(userId) {
    if (!confirm('Close this account? The user will no longer be able to sign in.')) return;
    await api(`/auth/users/${userId}`, { method: 'DELETE' });
    if (document.getElementById('account-admin-container')) {
        renderAccountAdminInline();
    } else {
        renderUserAdmin();
    }
}

async function init() {
    if (!getToken()) {
        renderLogin();
        return;
    }
    try {
        currentUser = await api('/auth/me');
        const complete = await api('/auth/me/complete');

        if (!complete.complete && currentUser.role === 'student') {
            renderProfileCompletion(complete.missing);
            return;
        }
        courses = await api('/courses');
        renderApp();
    } catch (e) {
        console.error('init failed:', e);
        clearToken();
        renderLogin();
    }
}

function renderProfileCompletion(missing) {
    document.getElementById('user-bar').innerHTML = '';
    document.getElementById('main').innerHTML = `
        <div class="card">
            <h2>Complete your profile</h2>
            <p>Please provide the following information before creating your study plan.</p>
            <div class="field">
                <label>First name</label>
                <input id="first-name" type="text" value="${escapeHtml(currentUser.first_name || '')}">
            </div>
            <div class="field">
                <label>Last name</label>
                <input id="last-name" type="text" value="${escapeHtml(currentUser.last_name || '')}">
            </div>
            <div class="field">
                <label>Personal number (YYYYMMDD-XXXX)</label>
                <input id="personal-number" type="text" value="${escapeHtml(currentUser.personal_number || '')}">
            </div>
            <div class="field">
                <label>Admission term</label>
                <select id="admission-term">${admissionTermOptions(currentUser.admission_term)}</select>
            </div>
            <button onclick="submitProfile()">Save</button>
            <div id="profile-error" style="color:var(--danger);margin-top:0.5rem"></div>
        </div>
    `;
}

async function submitProfile() {
    const first_name = document.getElementById('first-name').value.trim();
    const last_name = document.getElementById('last-name').value.trim();
    const personal_number = document.getElementById('personal-number').value.trim();
    const admission_term = document.getElementById('admission-term').value;

    try {
        currentUser = await api('/auth/me', {
            method: 'PATCH',
            body: { first_name, last_name, personal_number, admission_term }
        });
        courses = await api('/courses');
        renderApp();
    } catch (e) {
        document.getElementById('profile-error').textContent = e.message;
    }
}

function renderLogin() {
    const form = showRegister ? registerFormHtml() : loginFormHtml();
    document.getElementById('user-bar').innerHTML = '';
    document.getElementById('main').innerHTML = `
        <div class="card" id="login-form">
            ${form}
            <div id="login-error" style="color:var(--danger);margin-top:0.5rem"></div>
        </div>
    `;
}

function loginFormHtml() {
    return `
        <h2>Sign in</h2>
        <div class="field">
            <label>Email</label>
            <input id="login-email" type="email">
        </div>
        <div class="field">
            <label>Password</label>
            <input id="login-password" type="password">
        </div>
        <button onclick="submitLogin()">Sign in</button>
        <p style="margin-top:1rem">No account? <a href="#" onclick="toggleRegister()">Create one</a></p>
    `;
}

function registerFormHtml() {
    return `
        <h2>Create account</h2>
        <div class="field">
            <label>I am a</label>
            <select id="register-role" onchange="onRegisterRoleChange()">
                <option value="student">Student</option>
                <option value="director">Director</option>
            </select>
        </div>
        <div class="field">
            <label>Email</label>
            <input id="register-email" type="email">
        </div>
        <div class="field">
            <label>Password</label>
            <input id="register-password" type="password">
            <small>At least 10 characters, with uppercase, lowercase, digit, and special character.</small>
        </div>
        <div class="field">
            <label>First name</label>
            <input id="register-first-name" type="text">
        </div>
        <div class="field">
            <label>Last name</label>
            <input id="register-last-name" type="text">
        </div>
        <div id="student-fields">
            <div class="field">
                <label>Personal number (YYYYMMDD-XXXX)</label>
                <input id="register-personal-number" type="text">
            </div>
            <div class="field">
                <label>Admission term</label>
                <select id="register-admission-term">${admissionTermOptions()}</select>
            </div>
        </div>
        <div class="field" id="director-secret-field" style="display:none">
            <label>Director secret</label>
            <input id="register-director-secret" type="password">
        </div>
        <button onclick="submitRegister()">Create account</button>
        <p style="margin-top:1rem">Already have an account? <a href="#" onclick="toggleRegister()">Sign in</a></p>
    `;
}

function onRegisterRoleChange() {
    const role = document.getElementById('register-role').value;
    const studentFields = document.getElementById('student-fields');
    const secretField = document.getElementById('director-secret-field');
    if (role === 'director') {
        studentFields.style.display = 'none';
        secretField.style.display = 'block';
    } else {
        studentFields.style.display = 'block';
        secretField.style.display = 'none';
    }
}

function toggleRegister() {
    showRegister = !showRegister;
    renderLogin();
}

async function submitLogin() {
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;

    try {
        const data = await api('/auth/login', {
            method: 'POST',
            body: { email, password }
        });
        setToken(data.access_token);
        currentUser = data.user;
        init();
    } catch (e) {
        document.getElementById('login-error').textContent = e.message;
    }
}

async function submitRegister() {
    const role = document.getElementById('register-role').value;
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    const first_name = document.getElementById('register-first-name').value.trim();
    const last_name = document.getElementById('register-last-name').value.trim();

    const body = { email, password, first_name, last_name, role };

    if (role === 'student') {
        body.personal_number = document.getElementById('register-personal-number').value.trim();
        body.admission_term = document.getElementById('register-admission-term').value;
    } else if (role === 'director') {
        body.director_secret = document.getElementById('register-director-secret').value;
    }

    try {
        const data = await api('/auth/register', {
            method: 'POST',
            body,
        });
        setToken(data.access_token);
        currentUser = data.user;
        init();
    } catch (e) {
        document.getElementById('login-error').textContent = e.message;
    }
}


function logout() {
    clearToken();
    currentUser = null;
    renderLogin();
}

function renderApp() {
    document.getElementById('user-bar').innerHTML = `
        <span>${escapeHtml(formatUserName(currentUser))} (${escapeHtml(currentUser.role)})</span>
        <button class="secondary" onclick="logout()" style="margin-left:1rem">Logout</button>
    `;
    if (currentUser.role === 'student') renderStudent();
    else renderDirector();
}

function admissionTermOptions(selected = '') {
    const year = new Date().getFullYear();
    let opts = '<option value="">-- select admission term --</option>';
    for (let y = year - 1; y <= year + 3; y++) {
        const fallSelected = selected === `Fall ${y}` ? 'selected' : '';
        const springSelected = selected === `Spring ${y}` ? 'selected' : '';
        opts += `<option value="Fall ${y}" ${fallSelected}>Fall ${y}</option><option value="Spring ${y}" ${springSelected}>Spring ${y}</option>`;
    }
    return opts;
}

function getPlanTerms(admissionTerm) {
    if (!admissionTerm) return [];
    const [semester, yearStr] = admissionTerm.split(' ');
    let year = parseInt(yearStr, 10);
    let current = semester;
    const terms = [];
    for (let i = 0; i < TERM_COUNT; i++) {
        terms.push(`${current} ${year}`);
        if (current === 'Fall') {
            current = 'Spring';
            year++;
        } else {
            current = 'Fall';
        }
    }
    return terms;
}

function getSelectedCourseIds() {
    const ids = new Set();
    document.querySelectorAll('.course-row .course-select').forEach(select => {
        const value = select.value;
        if (value && value !== 'custom') {
            ids.add(parseInt(value, 10));
        }
    });
    return ids;
}

function courseOptionsForTerm(term, selectedCourseId = null) {
    const usedIds = getSelectedCourseIds();
    const catalogOptions = courses
        .filter(c => c.term === term && (!usedIds.has(c.id) || c.id === selectedCourseId))
        .map(c => `<option value="${c.id}">${escapeHtml(c.university)} ${escapeHtml(c.code)} — ${escapeHtml(c.title)} (${c.credits} cr)</option>`)
        .join('');
    return `
        <option value="">-- select course --</option>
        ${catalogOptions}
        <option value="custom">Non-program course…</option>
    `;
}

function getItemCredits(item) {
    if (item.credits) return item.credits;
    if (item.course) return item.course.credits;
    return 0;
}

function progressBarHtml(value, max, id = null) {
    const pct = Math.min(100, Math.max(0, Math.round((value / max) * 100)));
    let cls = '';
    if (value < CREDIT_MIN) cls = 'warning';
    else if (value > CREDIT_MAX) cls = 'warning';
    else if (value === CREDIT_TARGET) cls = 'ok';
    const idAttr = id ? `id="${id}"` : '';
    return `
        <div class="progress-bar" ${idAttr}>
            <div class="progress-fill ${cls}" style="width:${pct}%"></div>
            <span class="progress-label">${value}/${max} cr</span>
        </div>
    `;
}

function totalProgressHtml(total) {
    const pct = Math.round((total / TOTAL_CREDITS) * 100);
    const displayPct = Math.max(0, pct);
    const barWidth = Math.min(100, Math.max(0, pct));
    const cls = total >= TOTAL_CREDITS ? 'ok' : (total < TOTAL_CREDITS * 0.75 ? 'warning' : '');
    return `
        <div class="total-progress">
            <div class="total-progress-header">
                <strong>Program progress</strong>
                <span>${total}/${TOTAL_CREDITS} credits (${displayPct}%)</span>
            </div>
            <div class="total-progress-bar">
                <div class="total-progress-fill ${cls}" style="width:${barWidth}%"></div>
            </div>
        </div>
    `;
}

function calculateTermCreditsFromDom(term) {
    let total = 0;
    const rows = document.querySelectorAll(`#items-${term.replace(' ', '-')} .course-row`);
    rows.forEach(row => {
        const courseValue = row.querySelector('.course-select').value;
        if (!courseValue) return;
        if (courseValue === 'custom') {
            total += parseFloat(row.querySelector('.custom-credits').value) || 0;
        } else {
            const course = courses.find(c => c.id === parseInt(courseValue, 10));
            if (course) total += course.credits;
        }
    });
    return total;
}

function updateTermCredits(term) {
    const credits = calculateTermCreditsFromDom(term);
    const fill = document.querySelector(`#credits-${term.replace(' ', '-')} .progress-fill`);
    const label = document.querySelector(`#credits-${term.replace(' ', '-')} .progress-label`);
    if (fill && label) {
        const pct = Math.min(100, Math.max(0, Math.round((credits / CREDIT_TARGET) * 100)));
        fill.style.width = `${pct}%`;
        fill.className = `progress-fill ${
            credits < CREDIT_MIN ? 'warning' : credits > CREDIT_MAX ? 'warning' : credits === CREDIT_TARGET ? 'ok' : ''
        }`;
        label.textContent = `${credits}/${CREDIT_TARGET} cr`;
    }
    updateTotalProgress();
}

function updateTotalProgress() {
    const totalEl = document.getElementById('total-progress');
    if (!totalEl) return;
    let total = 0;
    if (currentUser.admission_term) {
        getPlanTerms(currentUser.admission_term).forEach(term => {
            total += calculateTermCreditsFromDom(term);
        });
    }
    totalEl.innerHTML = totalProgressHtml(total);
}

function refreshAllDropdownsForTerm(term) {
    const container = document.getElementById(`items-${term.replace(' ', '-')}`);
    if (!container) return;
    const rows = container.querySelectorAll('.course-row');
    rows.forEach(row => {
        const select = row.querySelector('.course-select');
        const currentValue = select.value;
        select.innerHTML = courseOptionsForTerm(term, currentValue ? parseInt(currentValue, 10) : null);
        select.value = currentValue;
    });
}

function onCourseChange(select, term) {
    const row = select.closest('.course-row');
    const value = select.value;
    const creditsInput = row.querySelector('.credits');
    const customFields = row.querySelector('.custom-fields');

    if (value === 'custom') {
        customFields.style.display = 'flex';
        creditsInput.value = '';
    } else if (value) {
        customFields.style.display = 'none';
        const course = courses.find(c => c.id === parseInt(value, 10));
        creditsInput.value = course ? course.credits : '';
    } else {
        customFields.style.display = 'none';
        creditsInput.value = '';
    }

    refreshAllDropdownsForTerm(term);
    updateTermCredits(term);
}

function removeCourseRow(button, term) {
    button.closest('.course-row').remove();
    refreshAllDropdownsForTerm(term);
    updateTermCredits(term);
}

function createCourseRowHtml(term, item = null) {
    const isCustom = item && !item.course_id;
    const customStyle = isCustom ? 'display:flex' : 'display:none';
    const courseOptions = courseOptionsForTerm(term, item?.course_id);

    return `
        <div class="course-row">
            <select class="course-select" onchange="onCourseChange(this, '${term}')">
                ${courseOptions}
            </select>
            <div class="credits-field">
                <input class="credits" type="number" disabled placeholder="cr">
            </div>
            <button class="secondary remove-btn" onclick="removeCourseRow(this, '${term}')" title="Remove course">✕</button>
            <div class="custom-fields" style="${customStyle}">
                <input class="custom-code" placeholder="Custom code" value="${escapeHtml(item?.custom_code || '')}">
                <input class="custom-title" placeholder="Custom title" value="${escapeHtml(item?.custom_title || '')}">
                <input class="custom-credits" type="number" placeholder="Credits" value="${item?.credits ?? ''}" oninput="updateTermCredits('${term}')">
            </div>
        </div>
    `;
}

function addCourseRow(term, item = null) {
    const container = document.getElementById(`items-${term.replace(' ', '-')}`);
    const wrapper = document.createElement('div');
    wrapper.innerHTML = createCourseRowHtml(term, item);
    const row = wrapper.firstElementChild;

    if (item) {
        const select = row.querySelector('.course-select');
        select.value = item.course_id || 'custom';
        if (item.custom_code) row.querySelector('.custom-code').value = item.custom_code;
        if (item.custom_title) row.querySelector('.custom-title').value = item.custom_title;
    }

    const hint = container.querySelector('.empty-term-hint');
    if (hint) hint.remove();

    container.appendChild(row);
    onCourseChange(row.querySelector('.course-select'), term);
}

function termCardHtml(term) {
    return `
        <div class="term-card">
            <div class="term-header">
                <span class="term-title">${term}</span>
                ${progressBarHtml(0, CREDIT_TARGET, `credits-${term.replace(' ', '-')}`)}
            </div>
            <div id="items-${term.replace(' ', '-')}" class="term-body">
                <div class="empty-term-hint">No courses added yet</div>
            </div>
            <button class="add-course-btn" onclick="addCourseRow('${term}')">+ Add Course</button>
        </div>
    `;
}

function renderTermSections() {
    const term = currentUser.admission_term;
    const container = document.getElementById('term-sections');
    if (!term) {
        container.innerHTML = '<p class="empty-term-hint">Please complete your profile with an admission term.</p>';
        updateTotalProgress();
        return;
    }
    container.innerHTML = getPlanTerms(term).map(termCardHtml).join('');
    updateTotalProgress();
}

function newPlan() {
    editingPlanId = null;
    document.getElementById('main').innerHTML = `
        <div class="card">
            <h2>New Study Plan</h2>
            <p>Admission term: <strong>${escapeHtml(currentUser.admission_term || '-')}</strong></p>
            <div id="term-sections"></div>
            <div id="total-progress"></div>
            <div class="actions">
                <button onclick="savePlan(false)">Save Draft</button>
            </div>
        </div>
    `;
    if (currentUser.admission_term) {
        renderTermSections();
    }
}

let editingPlanId = null;

async function editPlan(planId) {
    const plan = await api(`/plans/${planId}`);
    editingPlanId = planId;
    const latest = plan.versions[0];
    const admissionTerm = plan.student.admission_term;

    const itemsByTerm = {};
    getPlanTerms(admissionTerm).forEach(t => itemsByTerm[t] = []);
    latest.items.forEach(item => {
        const term = item.term || getPlanTerms(admissionTerm)[0];
        if (!itemsByTerm[term]) itemsByTerm[term] = [];
        itemsByTerm[term].push(item);
    });

    document.getElementById('main').innerHTML = `
        <div class="card">
            <h2>Edit Study Plan</h2>
            <p>Admission term: <strong>${escapeHtml(admissionTerm || '-')}</strong></p>
            <div id="term-sections"></div>
            <div id="total-progress"></div>
            <div class="actions">
                <button onclick="savePlan(true)">Save Update as Draft</button>
                <button class="secondary" onclick="renderApp()">Cancel</button>
            </div>
        </div>
    `;

    renderTermSections();

    getPlanTerms(admissionTerm).forEach(term => {
        const container = document.getElementById(`items-${term.replace(' ', '-')}`);
        container.innerHTML = '';
        const items = itemsByTerm[term] || [];
        if (items.length) {
            items.forEach(item => addCourseRow(term, item));
        } else {
            container.innerHTML = '<div class="empty-term-hint">No courses added yet</div>';
        }
    });
}

function findDuplicateCourseCodes() {
    const usedCodes = {};
    const duplicates = new Set();
    const admissionTerm = currentUser.admission_term;
    if (!admissionTerm) return [];

    getPlanTerms(admissionTerm).forEach(term => {
        const rows = document.querySelectorAll(`#items-${term.replace(' ', '-')} .course-row`);
        rows.forEach(row => {
            const courseValue = row.querySelector('.course-select').value;
            if (!courseValue) return;

            let code = null;
            if (courseValue === 'custom') {
                code = row.querySelector('.custom-code').value.trim();
            } else {
                const course = courses.find(c => c.id === parseInt(courseValue, 10));
                code = course ? course.code : null;
            }

            if (code) {
                if (usedCodes[code]) {
                    duplicates.add(code);
                } else {
                    usedCodes[code] = true;
                }
            }
        });
    });

    return Array.from(duplicates);
}

function collectPlanItems(admissionTerm) {
    const items = [];
    const errors = [];

    const duplicateCodes = findDuplicateCourseCodes();
    if (duplicateCodes.length) {
        errors.push(`Duplicate course(s) selected: ${duplicateCodes.join(', ')}. Each course can only be taken once.`);
    }

    getPlanTerms(admissionTerm).forEach(term => {
        const rows = document.querySelectorAll(`#items-${term.replace(' ', '-')} .course-row`);
        rows.forEach(row => {
            const courseValue = row.querySelector('.course-select').value;
            if (!courseValue) return;

            const isCustom = courseValue === 'custom';
            const isCatalog = courseValue && !isCustom;

            const customCode = row.querySelector('.custom-code').value.trim();
            const customTitle = row.querySelector('.custom-title').value.trim();
            const customCreditsRaw = row.querySelector('.custom-credits').value;
            const customCredits = customCreditsRaw ? parseFloat(customCreditsRaw) : null;

            if (isCustom) {
                if (!customCode) errors.push(`${term}: custom course code is missing`);
                if (!customTitle) errors.push(`${term}: custom course title is missing`);
                if (!customCredits || customCredits <= 0) errors.push(`${term}: custom course credits are missing or invalid`);
            }

            items.push({
                term,
                course_id: isCatalog ? parseInt(courseValue, 10) : null,
                custom_code: isCustom ? (customCode || null) : null,
                custom_title: isCustom ? (customTitle || null) : null,
                credits: isCustom ? customCredits : null,
            });
        });
    });

    return { items, errors };
}

async function savePlan(isUpdate) {
    const admissionTerm = currentUser.admission_term;

    if (!admissionTerm) {
        alert('Please complete your profile with an admission term.');
        return;
    }

    const { items, errors } = collectPlanItems(admissionTerm);

    if (errors.length) {
        alert('Please fix the following issues:\n\n' + errors.join('\n'));
        return;
    }

    if (isUpdate) {
        await api(`/plans/${editingPlanId}/update`, {
            method: 'POST',
            body: { title: null, items },
        });
    } else {
        await api('/plans', {
            method: 'POST',
            body: { title: null, items },
        });
    }
    renderApp();
}

function commentsHtml(comments) {
    return comments.map(c => `
        <div class="comment">
            <div class="comment-meta">${escapeHtml(formatUserName(c.author))} • ${new Date(c.created_at).toLocaleString()}</div>
            <div>${escapeHtml(c.text)}</div>
        </div>
    `).join('') || '<p class="muted">No comments yet.</p>';
}

function termProgressBarHtml(credits) {
    return progressBarHtml(credits, CREDIT_TARGET);
}

function itemsByTermHtml(admissionTerm, items) {
    if (!admissionTerm) return '<p class="muted">No admission term set.</p>';

    const grouped = {};
    const creditsByTerm = {};
    getPlanTerms(admissionTerm).forEach(t => {
        grouped[t] = [];
        creditsByTerm[t] = 0;
    });

    items.forEach(i => {
        const term = i.term || getPlanTerms(admissionTerm)[0];
        if (!grouped[term]) grouped[term] = [];
        grouped[term].push(i);
        creditsByTerm[term] = (creditsByTerm[term] || 0) + getItemCredits(i);
    });

    const totalCredits = items.reduce((sum, i) => sum + getItemCredits(i), 0);

    const termHtml = getPlanTerms(admissionTerm).map(term => {
        const termItems = grouped[term];
        if (!termItems.length) return '';
        const rows = termItems.map(i => `
            <tr>
                <td>${i.course ? `${escapeHtml(i.course.university)} ${escapeHtml(i.course.code)}` : (escapeHtml(i.custom_code) || '-')}</td>
                <td>${i.course ? escapeHtml(i.course.title) : (escapeHtml(i.custom_title) || '-')}</td>
                <td>${getItemCredits(i)}</td>
            </tr>
        `).join('');
        return `
            <div class="term-card readonly">
                <div class="term-header">
                    <span class="term-title">${term}</span>
                    ${termProgressBarHtml(creditsByTerm[term])}
                </div>
                <table>
                    <thead><tr><th>Code</th><th>Title</th><th>Credits</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        `;
    }).join('');

    return termHtml + totalProgressHtml(totalCredits);
}

function renderPlanView(plan, version, isLatest) {
    const versionButtons = plan.versions.map(v => {
        const active = v.version_number === version.version_number ? 'active' : '';
        return `<button class="version-btn ${active}" onclick="viewPlan(${plan.id}, ${v.version_number})">v${v.version_number}</button>`;
    }).join(' ');

    const diff = version.previous_version_number !== null
        ? `<div class="diff-summary"><strong>Changes from version ${version.previous_version_number}:</strong> ${escapeHtml(version.diff_summary)}</div>`
        : '';

    const flags = currentUser.role === 'director' && plan.student
        ? `<div class="flag-list">
             <label class="flag-item"><input type="checkbox" id="tuition-paying" onchange="saveDirectorFlags(${plan.student.id})"> <span>Tuition paying</span></label>
             <label class="flag-item"><input type="checkbox" id="registration-complete" onchange="saveDirectorFlags(${plan.student.id})"> <span>Registration complete</span></label>
             <span id="flag-save-status"></span>
           </div>`
        : `<span class="flag-badge">${plan.student.tuition_paying ? 'Tuition paying' : 'No tuition'}</span>
           <span class="flag-badge">${plan.student.registration_complete ? 'Registered' : 'Not registered'}</span>`;

    const header = `
        <div class="plan-header">
            <span class="header-value">${escapeHtml(formatUserName(plan.student))}</span>
            <span class="header-value">adm. ${plan.student.admission_term || '-'}</span>
            <span class="flags">${flags}</span>
            <span class="header-value"><span class="status ${plan.status}">${statusLabel(plan.status)}</span></span>
            <span class="version-badge">v${plan.current_version}</span>
        </div>
    `;

    let actions = `<button class="secondary" onclick="renderApp()">Back</button>`;

    if (currentUser.role === 'student' && plan.student_id === currentUser.id) {
        const editBtn = isLatest && plan.status !== 'pending'
            ? `<button onclick="editPlan(${plan.id})">Edit</button>`
            : `<button disabled class="disabled">Edit</button>`;
        const submitBtn = isLatest && plan.status !== 'pending'
            ? `<button class="success" onclick="submitPlan(${plan.id})">Submit</button>`
            : `<button disabled class="disabled success">Submit</button>`;
        actions += ` ${editBtn} ${submitBtn}`;
    }

    if (currentUser.role === 'director') {
        const approveBtn = isLatest && plan.status === 'pending'
            ? `<button class="success" onclick="decide(${plan.id}, 'approved')">Approve</button>`
            : `<button disabled class="disabled success">Approve</button>`;
        const rejectBtn = isLatest && plan.status === 'pending'
            ? `<button class="danger" onclick="decide(${plan.id}, 'rejected')">Reject</button>`
            : `<button disabled class="disabled danger">Reject</button>`;
        const requestBtn = isLatest && plan.status === 'pending'
            ? `<button onclick="requestChanges(${plan.id})">Request Changes</button>`
            : `<button disabled class="disabled">Request Changes</button>`;
        actions += ` ${approveBtn} ${rejectBtn} ${requestBtn}`;
    }

    const comments = commentsHtml(plan.comments);

    const commentBox = isLatest
        ? `<div class="card">
            <h3>Comments</h3>
            ${comments}
            <textarea id="comment-text" placeholder="Add a comment..." rows="2" style="margin-top:1rem"></textarea>
            <div class="actions"><button onclick="postComment(${plan.id})">Add Comment</button></div>
        </div>`
        : `<div class="card">
            <h3>Comments</h3>
            ${comments}
            <p class="muted">Commenting is disabled for older versions.</p>
        </div>`;

    document.getElementById('main').innerHTML = `
        <div class="card">
            ${header}
            ${diff}
            <h3>Courses</h3>
            ${itemsByTermHtml(plan.student.admission_term, version.items)}
            <div class="actions">${actions}</div>
        </div>
        ${commentBox}
    `;
}

async function saveDirectorFlags(userId) {
    const tuition_paying = document.getElementById('tuition-paying').checked;
    const registration_complete = document.getElementById('registration-complete').checked;
    await api(`/auth/users/${userId}/director-flags`, {
        method: 'PATCH',
        body: { tuition_paying, registration_complete }
    });
    const status = document.getElementById('flag-save-status');
    if (status) {
        status.textContent = 'Saved';
        setTimeout(() => status.textContent = '', 1500);
    }
}

async function loadDirectorFlags(userId) {
    const user = await api(`/auth/users/${userId}/director-flags`);
    const tuitionBox = document.getElementById('tuition-paying');
    const registrationBox = document.getElementById('registration-complete');
    if (tuitionBox) tuitionBox.checked = user.tuition_paying;
    if (registrationBox) registrationBox.checked = user.registration_complete;
}

async function viewPlan(planId, versionNumber) {
    const plan = await api(`/plans/${planId}`);
    versionNumber = versionNumber || plan.current_version;
    const version = await api(`/plans/${planId}/versions/${versionNumber}`);
    const isLatest = versionNumber === plan.current_version;
    renderPlanView(plan, version, isLatest);
    if (currentUser.role === 'director' && plan.student) {
        loadDirectorFlags(plan.student.id);
    }
}

async function renderStudent() {
    const plans = await api('/plans');
    const plan = plans[0];

    if (!plan) {
        document.getElementById('main').innerHTML = `
            <div class="card">
                <h2>My Study Plan</h2>
                <p>You don't have a study plan yet.</p>
                <button onclick="newPlan()">Create Study Plan</button>
            </div>
        `;
        return;
    }

    const latest = plan.versions[0];
    const canEdit = plan.status !== 'pending';
    const canSubmit = plan.status === 'draft' || plan.status === 'rejected' || plan.status === 'changes_requested';

    document.getElementById('main').innerHTML = `
        <div class="card">
            <h2>Study Plan</h2>
            <p>Admission term: ${plan.student.admission_term || '-'} • Status: <span class="status ${plan.status}">${statusLabel(plan.status)}</span> • Version ${latest.version_number}</p>
            ${itemsByTermHtml(plan.student.admission_term, latest.items)}
            <div class="actions">
                ${canEdit ? `<button onclick="editPlan(${plan.id})">${plan.status === 'approved' ? 'Update' : 'Edit'}</button>` : ''}
                ${canSubmit ? `<button class="success" onclick="submitPlan(${plan.id})">Submit for Approval</button>` : ''}
            </div>
        </div>
        <div class="card">
            <h3>Comments & Feedback</h3>
            ${commentsHtml(plan.comments)}
            <textarea id="comment-text" rows="3" placeholder="Add feedback..." style="margin-top:1rem"></textarea>
            <div class="actions">
                <button onclick="postComment(${plan.id})">Post Comment</button>
            </div>
        </div>
    `;
}

async function submitPlan(planId) {
    await api(`/plans/${planId}/submit`, { method: 'POST' });
    renderApp();
}

async function postComment(planId) {
    const text = document.getElementById('comment-text').value;
    if (!text.trim()) return;
    await api(`/plans/${planId}/comments`, { method: 'POST', body: { text } });
    if (currentUser.role === 'director') {
        viewPlan(planId);
    } else {
        renderStudent();
    }
}

async function decide(planId, decision) {
    const commentBox = document.getElementById('comment-text');
    const comment = commentBox ? commentBox.value : '';
    await api(`/plans/${planId}/decide`, {
        method: 'POST',
        body: { decision, comment: comment || null },
    });
    renderApp();
}

async function requestChanges(planId) {
    const commentBox = document.getElementById('comment-text');
    const comment = commentBox ? commentBox.value : '';
    await api(`/plans/${planId}/request-changes`, {
        method: 'POST',
        body: { decision: 'rejected', comment: comment || null },
    });
    renderApp();
}

async function renderDirector() {
    const plans = await api('/plans');

    const planRows = plans.map(p => `
        <tr>
            <td>${escapeHtml(formatUserName(p.student))}</td>
            <td>${p.student.admission_term || '-'}</td>
            <td><span class="status ${p.status}">${statusLabel(p.status)}</span></td>
            <td>v${p.current_version}</td>
            <td>${new Date(p.updated_at).toLocaleDateString()}</td>
            <td><button onclick="viewPlan(${p.id})">Review</button></td>
        </tr>
    `).join('');

    const terms = new Set();
    plans.forEach(p => {
        if (p.student.admission_term) {
            getPlanTerms(p.student.admission_term).forEach(t => terms.add(t));
        }
    });
    const termOptions = Array.from(terms).sort().map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('');

    document.getElementById('main').innerHTML = `
        <div class="card">
            <h2>Director Dashboard</h2>
            <div class="tabs">
                <button class="tab active" onclick="switchTab('plans')" id="tab-plans">Study Plans</button>
                <button class="tab" onclick="switchTab('courses')" id="tab-courses">Courses</button>
                <button class="tab" onclick="switchTab('registrations')" id="tab-registrations">Registrations</button>
                <button class="tab" onclick="switchTab('accounts')" id="tab-accounts">Accounts</button>
            </div>

            <div id="tab-content-plans" class="tab-content active">
                <table>
                    <thead>
                        <tr><th>Student</th><th>Admission</th><th>Status</th><th>Version</th><th>Updated</th><th>Actions</th></tr>
                    </thead>
                    <tbody>${planRows || '<tr><td colspan="6">No plans yet.</td></tr>'}</tbody>
                </table>
            </div>

            <div id="tab-content-courses" class="tab-content" style="display:none">
                <div id="course-admin-container"></div>
            </div>

            <div id="tab-content-registrations" class="tab-content" style="display:none">
                <div class="form-row">
                    <select id="export-term">
                        <option value="">-- select term --</option>
                        ${termOptions || '<option value="">No terms available</option>'}
                    </select>
                    <button onclick="exportSelectedTerm()">Download CSV</button>
                </div>
                <p>Select a term and download the full registration matrix.</p>
            </div>

            <div id="tab-content-accounts" class="tab-content" style="display:none">
                <div id="account-admin-container"></div>
            </div>
        </div>
    `;

    renderCourseAdminInline();
}

async function renderCourseAdminInline() {
    const container = document.getElementById('course-admin-container');
    if (!container) return;
    const allCourses = await api('/courses');
    const rows = allCourses.map(c => `
        <tr>
            <td>${escapeHtml(c.university)}</td>
            <td>${escapeHtml(c.code)}</td>
            <td>${escapeHtml(c.title)}</td>
            <td>${c.credits}</td>
            <td>${escapeHtml(c.term)}</td>
            <td><button onclick="deleteCourse(${c.id})">Delete</button></td>
        </tr>
    `).join('');

    container.innerHTML = `
        <h3>Add Course</h3>
        <div class="course-entry-row">
            <input id="course-university" type="text" placeholder="University">
            <input id="course-code" type="text" placeholder="Code">
            <input id="course-title" type="text" placeholder="Title">
            <input id="course-credits" type="number" step="0.1" placeholder="Credits">
            <input id="course-term" type="text" placeholder="Term">
            <button onclick="addCourse()">Add</button>
        </div>
        <div id="course-error" style="color:var(--danger);margin-top:0.5rem"></div>

        <h3 style="margin-top:1.5rem">Bulk Upload CSV</h3>
        <p>Upload a CSV with columns: university, code, title, credits, term</p>
        <div class="course-entry-row">
            <input type="file" id="course-file" accept=".csv">
            <button onclick="importCoursesCsv()">Upload</button>
        </div>

        <h3 style="margin-top:1.5rem">All Courses</h3>
        <table>
            <thead>
                <tr><th>University</th><th>Code</th><th>Title</th><th>Credits</th><th>Term</th><th>Actions</th></tr>
            </thead>
            <tbody>${rows || '<tr><td colspan="6">No courses yet.</td></tr>'}</tbody>
        </table>
    `;
}

function switchTab(name) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
    document.getElementById(`tab-${name}`).classList.add('active');
    document.getElementById(`tab-content-${name}`).style.display = 'block';

    if (name === 'accounts') {
        renderAccountAdminInline();
    } else if (name === 'courses') {
        renderCourseAdminInline();
    }
}

async function exportTermCsv(term) {
    const token = getToken();
    const res = await fetch(`${API}/plans/export/${encodeURIComponent(term)}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Export failed' }));
        alert(err.detail || 'Export failed');
        return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `registrations_${term.replace(' ', '_')}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

function exportSelectedTerm() {
    const term = document.getElementById('export-term').value;
    if (!term) {
        alert('Please select a term.');
        return;
    }
    exportTermCsv(term);
}

async function renderCourseAdmin() {
    courses = await api('/courses');
    const rows = courses.map(c => `
        <tr>
            <td>${escapeHtml(c.university)}</td>
            <td>${escapeHtml(c.code)}</td>
            <td>${escapeHtml(c.title)}</td>
            <td>${c.credits}</td>
            <td>${escapeHtml(c.term)}</td>
            <td><button class="secondary" onclick="deleteCourse(${c.id})">Delete</button></td>
        </tr>
    `).join('');

    document.getElementById('main').innerHTML = `
        <div class="card">
            <h2>Course Administration</h2>
            <h3>Add Course</h3>
            <div class="form-row">
                <input id="course-university" placeholder="University (KTH/SU)">
                <input id="course-code" placeholder="Code">
                <input id="course-title" placeholder="Title">
                <input id="course-credits" type="number" placeholder="Credits">
                <input id="course-term" placeholder="Term (e.g. Fall 2026)">
                <button onclick="addCourse()">Add</button>
            </div>
            <h3>Import CSV</h3>
            <input type="file" id="course-csv" accept=".csv">
            <button onclick="importCourseCsv()">Import</button>
            <h3>All Courses</h3>
            <table>
                <thead><tr><th>University</th><th>Code</th><th>Title</th><th>Credits</th><th>Term</th><th>Actions</th></tr></thead>
                <tbody>${rows || '<tr><td colspan="6">No courses.</td></tr>'}</tbody>
            </table>
            <div class="actions">
                <button class="secondary" onclick="renderApp()">Back</button>
            </div>
        </div>
    `;
}

async function addCourse() {
    const university = document.getElementById('course-university').value.trim();
    const code = document.getElementById('course-code').value.trim();
    const title = document.getElementById('course-title').value.trim();
    const credits = parseFloat(document.getElementById('course-credits').value);
    const term = document.getElementById('course-term').value.trim();

    if (!university || !code || !title || !credits || !term) {
        alert('Please fill in all fields.');
        return;
    }

    await api('/admin/courses', {
        method: 'POST',
        body: { university, code, title, credits, term },
    });
    renderCourseAdmin();
}

async function deleteCourse(courseId) {
    if (!confirm('Delete this course?')) return;
    await api(`/admin/courses/${courseId}`, { method: 'DELETE' });
    renderCourseAdmin();
}

async function importCourseCsv() {
    const input = document.getElementById('course-file');
    if (!input.files.length) {
        alert('Please select a CSV file.');
        return;
    }

    const formData = new FormData();
    formData.append('file', input.files[0]);

    const token = getToken();
    const res = await fetch(`${API}/admin/courses/import`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        body: formData,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Import failed' }));
        alert(err.detail || 'Import failed');
        return;
    }
    alert('Import successful');
    await renderCourseAdminInline();
}

init();
