# FrontShiftAI Administrator Guide

This guide is for **Company Admins** and **Super Admins** responsible for managing the FrontShiftAI platform.

## 1. Accessing the Admin Dashboard

*   Log in with your administrator credentials.
*   The system detects your role and automatically redirects you to the **Admin Dashboard** instead of the User Chat interface.

---

## 2. Monitoring Dashboard

The **Monitoring Dashboard** provides real-time insights into system performance and usage.

### Key Metrics
*   **Request Count**: Total number of interactions over time.
*   **Error Rate**: Percentage of failed requests (alerts triggered if >5%).
*   **Response Time**: Average latency for API calls (alerts triggered if >3s).
*   **Agent Usage**: Breakdown of interactions by agent type (RAG, PTO, HR).

### Alerts
*   The system automatically flags anomalies. Check the **Recent Errors** table for details on failed interactions.

---

## 3. User Management

### Managing Employees
*   View a list of all users in your organization.
*   **Add User**: Create new employee accounts with specific roles (User, Company Admin).
*   **Edit User**: Update details or reset passwords.
*   **Deactivate**: Remove access for terminated employees.

---

## 4. PTO Management

### Approving Requests
*   Navigate to the **PTO Management** section.
*   View all **Pending** requests from employees.
*   **Action**: Click **Approve** or **Reject** for each request.
*   *Note: Approved requests automatically deduct from the employee's balance.*

### Verification
*   The system prevents overdrafts (requesting more days than available).
*   Admins can manually adjust balances if necessary (e.g., carrying over days).

---

## 5. HR Ticket Management

### Handling Tickets
*   Navigate to the **HR Tickets** section.
*   View the queue of open support tickets.
*   **Prioritize**: Tickets are listed by urgency and wait time.
*   **Resolve**: Mark tickets as "Resolved" once the issue is addressed.
*   **Schedule**: If a meeting is required, use the external scheduling tool linked in the ticket details.

---

## 6. System Configuration (Super Admin Only)

### Company Management
*   Onboard new companies (tenants).
*   Upload and index new employee handbooks (PDFs) for RAG.
*   Configure company-specific policies (holidays, work hours).

### Maintenance
*   **Retraining**: Trigger a re-indexing of the vector database when handbooks change.
*   **Logs**: Access detailed server logs for debugging via Google Cloud Logging.
