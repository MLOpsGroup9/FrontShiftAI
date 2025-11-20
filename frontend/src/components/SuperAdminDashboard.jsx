import React, { useState, useEffect } from 'react';
import axios from 'axios';

const SuperAdminDashboard = ({ onLogout, userInfo }) => {
  const [companyAdmins, setCompanyAdmins] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  
  // Form state
  const [newAdmin, setNewAdmin] = useState({
    email: '',
    password: '',
    name: '',
    company: ''
  });

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      
      const [adminsRes, companiesRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/api/admin/company-admins`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_BASE_URL}/api/admin/all-companies`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      
      setCompanyAdmins(adminsRes.data.admins);
      setCompanies(companiesRes.data.companies);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddAdmin = async (e) => {
    e.preventDefault();
    
    try {
      const token = localStorage.getItem('access_token');
      await axios.post(
        `${API_BASE_URL}/api/admin/add-company-admin`,
        newAdmin,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setShowAddForm(false);
      setNewAdmin({ email: '', password: '', name: '', company: '' });
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to add admin');
    }
  };

  const handleDeleteAdmin = async (email) => {
    if (!confirm(`Delete admin: ${email}?`)) return;
    
    try {
      const token = localStorage.getItem('access_token');
      await axios.delete(`${API_BASE_URL}/api/admin/delete-company-admin`, {
        headers: { Authorization: `Bearer ${token}` },
        data: { email }
      });
      
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to delete admin');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0f] via-[#1a1a24] to-[#0a0a0f] p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Super Admin Dashboard</h1>
            <p className="text-white/60">Manage company admins across all organizations</p>
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
          <p className="text-white/60 text-sm mb-2">Total Companies</p>
          <p className="text-3xl font-bold text-white">{companies.length}</p>
        </div>
        <div className="glass-card bg-white/10 p-6">
          <p className="text-white/60 text-sm mb-2">Company Admins</p>
          <p className="text-3xl font-bold text-white">{companyAdmins.length}</p>
        </div>
        <div className="glass-card bg-white/10 p-6">
          <p className="text-white/60 text-sm mb-2">Your Role</p>
          <p className="text-lg font-semibold text-white">Super Administrator</p>
        </div>
      </div>

      {/* Company Admins Table */}
      <div className="max-w-7xl mx-auto">
        <div className="glass-card bg-white/10 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-white">Company Administrators</h2>
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="px-4 py-2 bg-white/90 hover:bg-white text-black rounded-lg transition-all"
            >
              {showAddForm ? 'Cancel' : '+ Add Admin'}
            </button>
          </div>

          {/* Add Admin Form */}
          {showAddForm && (
            <form onSubmit={handleAddAdmin} className="mb-6 p-4 bg-white/5 rounded-lg border border-white/10">
              <div className="grid grid-cols-2 gap-4">
                <input
                  type="email"
                  placeholder="Email"
                  value={newAdmin.email}
                  onChange={(e) => setNewAdmin({...newAdmin, email: e.target.value})}
                  required
                  className="px-4 py-2 bg-white/10 border border-white/10 rounded-lg text-white placeholder-white/40"
                />
                <input
                  type="password"
                  placeholder="Password"
                  value={newAdmin.password}
                  onChange={(e) => setNewAdmin({...newAdmin, password: e.target.value})}
                  required
                  className="px-4 py-2 bg-white/10 border border-white/10 rounded-lg text-white placeholder-white/40"
                />
                <input
                  type="text"
                  placeholder="Name"
                  value={newAdmin.name}
                  onChange={(e) => setNewAdmin({...newAdmin, name: e.target.value})}
                  required
                  className="px-4 py-2 bg-white/10 border border-white/10 rounded-lg text-white placeholder-white/40"
                />
                <select
                  value={newAdmin.company}
                  onChange={(e) => setNewAdmin({...newAdmin, company: e.target.value})}
                  required
                  className="px-4 py-2 bg-white/10 border border-white/10 rounded-lg text-white"
                >
                  <option value="">Select Company</option>
                  {companies.map(c => (
                    <option key={c.name} value={c.name}>{c.name}</option>
                  ))}
                </select>
              </div>
              <button
                type="submit"
                className="mt-4 px-6 py-2 bg-white/90 hover:bg-white text-black rounded-lg transition-all"
              >
                Add Administrator
              </button>
            </form>
          )}

          {/* Table */}
          {isLoading ? (
            <p className="text-white/60 text-center py-8">Loading...</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left py-3 px-4 text-white/80 font-medium">Name</th>
                    <th className="text-left py-3 px-4 text-white/80 font-medium">Email</th>
                    <th className="text-left py-3 px-4 text-white/80 font-medium">Company</th>
                    <th className="text-left py-3 px-4 text-white/80 font-medium">Created</th>
                    <th className="text-right py-3 px-4 text-white/80 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {companyAdmins.map(admin => (
                    <tr key={admin.email} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-3 px-4 text-white">{admin.name}</td>
                      <td className="py-3 px-4 text-white/70">{admin.email}</td>
                      <td className="py-3 px-4 text-white/70">{admin.company}</td>
                      <td className="py-3 px-4 text-white/50 text-sm">
                        {admin.created_at ? new Date(admin.created_at).toLocaleDateString() : 'N/A'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleDeleteAdmin(admin.email)}
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

export default SuperAdminDashboard;