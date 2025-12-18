
// const BASE_URL = "http://localhost:8000"; // Local
const BASE_URL = "/api";

const auth = {
    login: async (username, password) => {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const res = await fetch(`${BASE_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData
        });

        if (!res.ok) throw new Error("Login failed");

        const data = await res.json();
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('role', data.role);
        return data;
    },

    logout: () => {
        localStorage.removeItem('token');
        localStorage.removeItem('role');
        window.location.href = 'login.html';
    },

    getToken: () => localStorage.getItem('token'),
    getRole: () => localStorage.getItem('role'),

    check: () => {
        if (!localStorage.getItem('token')) {
            window.location.href = 'login.html';
        }
    }
};

async function apiFetch(endpoint, options = {}) {
    const token = auth.getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
        headers
    });

    if (res.status === 401) {
        auth.logout();
    }

    return res;
}
