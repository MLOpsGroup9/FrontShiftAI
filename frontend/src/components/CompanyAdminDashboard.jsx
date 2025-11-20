import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  getAllPTOBalances, 
  getAllPTORequests, 
  approvePTORequest, 
  updatePTOBalance,
  resetPTOBalance,
  resetAllPTOBalances,
  deletePTOBalance
} from '../services/api';

const CompanyAdminDashboard = ({ onLogout, userInfo }) => {
  const [activeTab, setActiveTab] = useState('users'); // users, leaves, requests
  const [users, setUsers] = useState([]);
  const [ptoBalances, setPtoBalances] = useState([]);
  const [ptoRequests, setPtoRequests] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');
  const [editingBalance, setEditingBalance] = useState(null);
  
  // Form state
  const [newUser, setNewUser] = useState({
    email: '',
    password: '',
    name: ''
  });

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (activeTab === 'users') {
      fetchUsers();
    } else if (activeTab === 'leaves') {
      fetchPTOBalances();
    } else if (activeTab === 'requests') {
      fetchPTORequests();
    }
  }, [activeTab, statusFilter]);

  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(`${API_BASE_URL}/api/admin/company-users`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUsers(response.data.users);
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchPTOBalances = async () => {
    setIsLoading(true);
    try {
      const balances = await getAllPTOBalances();
      setPtoBalances(balances);
    } catch (error) {
      console.error('Error fetching PTO balances:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchPTORequests = async () => {
    setIsLoading(true);
    try {
      const filter = statusFilter === 'all' ? null : statusFilter;
      const requests = await getAllPTORequests(filter);
      setPtoRequests(requests);
    } catch (error) {
      console.error('Error fetching PTO requests:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddUser = async (e) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem('access_token');
      await axios.post(
        `${API_BASE_URL}/api/admin/add-user`,
        newUser,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setShowAddForm(false);
      setNewUser({ email: '', password: '', name: '' });
      fetchUsers();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to add user');
    }
  };

  const handleDeleteUser = async (email) => {
    if (!confirm(`Delete user: ${email}?`)) return;
    try {
      const token = localStorage.getItem('access_token');
      await axios.delete(`${API_BASE_URL}/api/admin/delete-user`, {
        headers: { Authorization: `Bearer ${token}` },
        data: { email }
      });
      fetchUsers();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to delete user');
    }
  };

  const handleUpdatePassword = async (email) => {
    const newPassword = prompt(`Enter new password for ${email}:`);
    if (!newPassword) return;
    try {
      const token = localStorage.getItem('access_token');
      await axios.put(
        `${API_BASE_URL}/api/admin/update-password`,
        { email, new_password: newPassword },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      alert('Password updated successfully');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to update password');
    }
  };

  const handleUpdateBalance = async (email, newTotal) => {
    try {
      await updatePTOBalance(email, parseFloat(newTotal));
      setEditingBalance(null);
      fetchPTOBalances();
      alert('Balance updated successfully');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to update balance');
    }
  };

  const handleResetBalance = async (email) => {
    if (!confirm(`Reset used and pending days for ${email}?`)) return;
    try {
      await resetPTOBalance(email);
      fetchPTOBalances();
      alert('Balance reset successfully');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to reset balance');
    }
  };

  const handleResetAllBalances = async () => {
    if (!confirm('Reset ALL employee balances? This will set used and pending days to 0 for everyone.')) return;
    try {
      const result = await resetAllPTOBalances();
      fetchPTOBalances();
      alert(`Successfully reset balances for ${result.employees_reset} employees`);
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to reset all balances');
    }
  };

  const handleApproveRequest = async (requestId, status) => {
    const notes = status === 'denied' ? prompt('Reason for denial (optional):') : null;
    try {
      await approvePTORequest(requestId, status, notes);
      fetchPTORequests();
      alert(`Request ${status} successfully`);
    } catch (error) {
      alert(error.response?.data?.detail || `Failed to ${status} request`);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'text-yellow-400 bg-yellow-500/20 border-yellow-500/30';
      case 'approved': return 'text-green-400 bg-green-500/20 border-green-500/30';
      case 'denied': return 'text-red-400 bg-red-500/20 border-red-500/30';
      default: return 'text-white/60 bg-white/10 border-white/20';
    }
  };

  const getEmailDomain = () => {
    const company = userInfo?.company || '';
    return company.toLowerCase().replace(/[^a-z0-9]/g, '') + '.com';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0f] via-[#1a1a24] to-[#0a0a0f] p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Company Admin Dashboard</h1>
            <p className="text-white/60">Manage {userInfo?.company}</p>
          </div>
          <button
            onClick={onLogout}
            className="px-4 py-2 bg-white/10 hover:bg-white/15 border border-white/10 rounded-lg text-white transition-all"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="flex space-x-2 bg-white/5 p-1 rounded-lg border border-white/10">
          <button
            onClick={() => setActiveTab('users')}
            className={`flex-1 px-4 py-2 rounded-lg transition-all ${
              activeTab === 'users'
                ? 'bg-white/10 text-white'
                : 'text-white/60 hover:text-white hover:bg-white/5'
            }`}
          >
            👥 Users
          </button>
          <button
            onClick={() => setActiveTab('leaves')}
            className={`flex-1 px-4 py-2 rounded-lg transition-all ${
              activeTab === 'leaves'
                ? 'bg-white/10 text-white'
                : 'text-white/60 hover:text-white hover:bg-white/5'
            }`}
          >
            📊 Leave Balances
          </button>
          <button
            onClick={() => setActiveTab('requests')}
            className={`flex-1 px-4 py-2 rounded-lg transition-all ${
              activeTab === 'requests'
                ? 'bg-white/10 text-white'
                : 'text-white/60 hover:text-white hover:bg-white/5'
            }`}
          >
            📝 Leave Requests
          </button>
        </div>
      </div>

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div className="max-w-7xl mx-auto">
          <div className="glass-card bg-white/10 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">Company Users</h2>
              <button
                onClick={() => setShowAddForm(!showAddForm)}
                className="px-4 py-2 bg-white/90 hover:bg-white text-black rounded-lg transition-all"
              >
                {showAddForm ? 'Cancel' : '+ Add User'}
              </button>
            </div>

            {showAddForm && (
              <form onSubmit={handleAddUser} className="mb-6 p-4 bg-white/5 rounded-lg border border-white/10">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-white/60 text-sm mb-2">Email</label>
                    <input
                      type="email"
                      placeholder={`user@${getEmailDomain()}`}
                      value={newUser.email}
                      onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                      required
                      className="w-full px-4 py-2 bg-white/10 border border-white/10 rounded-lg text-white placeholder-white/40"
                    />
                  </div>
                  <div>
                    <label className="block text-white/60 text-sm mb-2">Password</label>
                    <input
                      type="password"
                      placeholder="Password"
                      value={newUser.password}
                      onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                      required
                      className="w-full px-4 py-2 bg-white/10 border border-white/10 rounded-lg text-white placeholder-white/40"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-white/60 text-sm mb-2">Full Name</label>
                    <input
                      type="text"
                      placeholder="John Doe"
                      value={newUser.name}
                      onChange={(e) => setNewUser({...newUser, name: e.target.value})}
                      required
                      className="w-full px-4 py-2 bg-white/10 border border-white/10 rounded-lg text-white placeholder-white/40"
                    />
                  </div>
                </div>
                <button
                  type="submit"
                  className="mt-4 px-6 py-2 bg-white/90 hover:bg-white text-black rounded-lg transition-all"
                >
                  Add User
                </button>
              </form>
            )}

            {isLoading ? (
              <p className="text-white/60 text-center py-8">Loading...</p>
            ) : users.length === 0 ? (
              <p className="text-white/60 text-center py-8">No users yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-left py-3 px-4 text-white/80 font-medium">Name</th>
                      <th className="text-left py-3 px-4 text-white/80 font-medium">Email</th>
                      <th className="text-left py-3 px-4 text-white/80 font-medium">Password</th>
                      <th className="text-right py-3 px-4 text-white/80 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map(user => (
                      <tr key={user.email} className="border-b border-white/5 hover:bg-white/5">
                        <td className="py-3 px-4 text-white">{user.name}</td>
                        <td className="py-3 px-4 text-white/70">{user.email}</td>
                        <td className="py-3 px-4 text-white/50 font-mono text-sm">{user.password}</td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => handleUpdatePassword(user.email)}
                            className="px-3 py-1 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded text-blue-300 text-sm transition-all mr-2"
                          >
                            Change Password
                          </button>
                          <button
                            onClick={() => handleDeleteUser(user.email)}
                            className="px-3 py-1 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 rounded text-red-300 text-sm transition-all"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Leave Balances Tab */}
      {activeTab === 'leaves' && (
        <div className="max-w-7xl mx-auto">
          <div className="glass-card bg-white/10 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">Employee Leave Balances</h2>
              <button
                onClick={handleResetAllBalances}
                className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-300 rounded-lg transition-all"
              >
                Reset All Balances
              </button>
            </div>

            {isLoading ? (
              <p className="text-white/60 text-center py-8">Loading...</p>
            ) : ptoBalances.length === 0 ? (
              <p className="text-white/60 text-center py-8">No leave balances found.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-left py-3 px-4 text-white/80 font-medium">Employee</th>
                      <th className="text-center py-3 px-4 text-white/80 font-medium">Total</th>
                      <th className="text-center py-3 px-4 text-white/80 font-medium">Used</th>
                      <th className="text-center py-3 px-4 text-white/80 font-medium">Pending</th>
                      <th className="text-center py-3 px-4 text-white/80 font-medium">Available</th>
                      <th className="text-right py-3 px-4 text-white/80 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ptoBalances.map(balance => (
                      <tr key={balance.email} className="border-b border-white/5 hover:bg-white/5">
                        <td className="py-3 px-4 text-white">{balance.email}</td>
                        <td className="py-3 px-4 text-center">
                          {editingBalance === balance.email ? (
                            <input
                              type="number"
                              step="0.5"
                              defaultValue={balance.total_days}
                              onBlur={(e) => handleUpdateBalance(balance.email, e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleUpdateBalance(balance.email, e.target.value);
                                if (e.key === 'Escape') setEditingBalance(null);
                              }}
                              autoFocus
                              className="w-20 px-2 py-1 bg-white/10 border border-white/20 rounded text-white text-center"
                            />
                          ) : (
                            <button
                              onClick={() => setEditingBalance(balance.email)}
                              className="text-white/90 hover:text-white"
                            >
                              {balance.total_days} days
                            </button>
                          )}
                        </td>
                        <td className="py-3 px-4 text-center text-white/70">{balance.used_days} days</td>
                        <td className="py-3 px-4 text-center text-yellow-400">{balance.pending_days} days</td>
                        <td className="py-3 px-4 text-center text-green-400 font-semibold">{balance.remaining_days} days</td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => handleResetBalance(balance.email)}
                            className="px-3 py-1 bg-orange-500/20 hover:bg-orange-500/30 border border-orange-500/30 rounded text-orange-300 text-sm transition-all"
                          >
                            Reset
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Leave Requests Tab */}
      {activeTab === 'requests' && (
        <div className="max-w-7xl mx-auto">
          <div className="glass-card bg-white/10 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">Leave Requests</h2>
              <div className="flex space-x-2">
                {['all', 'pending', 'approved', 'denied'].map(filter => (
                  <button
                    key={filter}
                    onClick={() => setStatusFilter(filter)}
                    className={`px-3 py-1 rounded-lg text-sm transition-all ${
                      statusFilter === filter
                        ? 'bg-white/20 text-white'
                        : 'bg-white/5 text-white/60 hover:text-white hover:bg-white/10'
                    }`}
                  >
                    {filter.charAt(0).toUpperCase() + filter.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {isLoading ? (
              <p className="text-white/60 text-center py-8">Loading...</p>
            ) : ptoRequests.length === 0 ? (
              <p className="text-white/60 text-center py-8">No leave requests found.</p>
            ) : (
              <div className="space-y-4">
                {ptoRequests.map(request => (
                  <div
                    key={request.id}
                    className="p-4 bg-white/5 rounded-lg border border-white/10 hover:bg-white/8 transition-all"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <h3 className="text-lg font-medium text-white">{request.email}</h3>
                          <span className={`px-2 py-1 rounded text-xs border ${getStatusColor(request.status)}`}>
                            {request.status}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <p className="text-white/50 mb-1">Dates</p>
                            <p className="text-white/90">
                              {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()}
                            </p>
                          </div>
                          <div>
                            <p className="text-white/50 mb-1">Days Requested</p>
                            <p className="text-white/90">{request.days_requested} days</p>
                          </div>
                          {request.reason && (
                            <div className="col-span-2">
                              <p className="text-white/50 mb-1">Reason</p>
                              <p className="text-white/70">{request.reason}</p>
                            </div>
                          )}
                          {request.admin_notes && (
                            <div className="col-span-2">
                              <p className="text-white/50 mb-1">Admin Notes</p>
                              <p className="text-white/70">{request.admin_notes}</p>
                            </div>
                          )}
                        </div>
                      </div>
                      {request.status === 'pending' && (
                        <div className="flex space-x-2 ml-4">
                          <button
                            onClick={() => handleApproveRequest(request.id, 'approved')}
                            className="px-4 py-2 bg-green-500/20 hover:bg-green-500/30 border border-green-500/30 rounded text-green-300 transition-all"
                          >
                            ✓ Approve
                          </button>
                          <button
                            onClick={() => handleApproveRequest(request.id, 'denied')}
                            className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 rounded text-red-300 transition-all"
                          >
                            ✗ Deny
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CompanyAdminDashboard;