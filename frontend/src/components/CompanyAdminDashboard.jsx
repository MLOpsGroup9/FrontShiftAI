import React, { useState, useEffect } from 'react';
import axios from 'axios';

const CompanyAdminDashboard = ({ onLogout, userInfo }) => {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  
  // Form state
  const [newUser, setNewUser] = useState({
    email: '',
    password: '',
    name: ''
  });

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchUsers();
  }, []);

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
      fetchUsers();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to update password');
    }
  };

  // Extract domain from company for email domain
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
            <p className="text-white/60">Manage users for {userInfo?.company}</p>
          </div>
          <button
            onClick={onLogout}
            className="px-4 py-2 bg-white/10 hover:bg-white/15 border border-white/10 rounded-lg text-white transition-all"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="glass-card bg-white/10 p-6">
          <p className="text-white/60 text-sm mb-2">Company</p>
          <p className="text-lg font-semibold text-white">{userInfo?.company}</p>
        </div>
        <div className="glass-card bg-white/10 p-6">
          <p className="text-white/60 text-sm mb-2">Total Users</p>
          <p className="text-3xl font-bold text-white">{users.length}</p>
        </div>
        <div className="glass-card bg-white/10 p-6">
          <p className="text-white/60 text-sm mb-2">Your Role</p>
          <p className="text-lg font-semibold text-white">Company Administrator</p>
        </div>
      </div>

      {/* Users Table */}
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

          {/* Add User Form */}
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

          {/* Table */}
          {isLoading ? (
            <p className="text-white/60 text-center py-8">Loading...</p>
          ) : users.length === 0 ? (
            <p className="text-white/60 text-center py-8">No users yet. Add your first user!</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left py-3 px-4 text-white/80 font-medium">Name</th>
                    <th className="text-left py-3 px-4 text-white/80 font-medium">Email</th>
                    <th className="text-left py-3 px-4 text-white/80 font-medium">Password</th>
                    <th className="text-left py-3 px-4 text-white/80 font-medium">Created</th>
                    <th className="text-right py-3 px-4 text-white/80 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map(user => (
                    <tr key={user.email} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-3 px-4 text-white">{user.name}</td>
                      <td className="py-3 px-4 text-white/70">{user.email}</td>
                      <td className="py-3 px-4 text-white/50 font-mono text-sm">
                        {user.password}
                      </td>
                      <td className="py-3 px-4 text-white/50 text-sm">
                        {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                      </td>
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
    </div>
  );
};

export default CompanyAdminDashboard;