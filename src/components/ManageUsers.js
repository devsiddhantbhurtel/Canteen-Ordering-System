const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this user?')) {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          throw new Error('No authentication token found');
        }

        await axios.delete(
          `${config.API_BASE_URL}/admin/users/${id}/`,
          {
            headers: {
              'Authorization': `${config.TOKEN_PREFIX} ${token}`,
              'Content-Type': 'application/json'
            }
          }
        );
        fetchUsers();
        toast.success('User deleted successfully');
      } catch (err) {
        console.error('Delete error:', err.response?.data || err.message);
        const errorMessage = err.response?.status === 500 
          ? 'Cannot delete user. They may have associated records in the system.'
          : 'Failed to delete user. Please try again.';
        toast.error(errorMessage);
      }
    }
  };