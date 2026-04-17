import { Navigate } from "react-router-dom";
import { useEffect, useState } from "react";

const ProtectedRoutes = ({ children }) => {
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    // Check JWT token validity
    const token = localStorage.getItem("token");
    setUser(token ? true : null);
  }, []);

  if (user === undefined) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <p className="text-slate-600 font-medium">Loading...</p>
      </div>
    );
  }

  return user ? children : <Navigate to="/login" replace />;
};

export default ProtectedRoutes;
