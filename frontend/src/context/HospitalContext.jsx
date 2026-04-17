import React, { createContext, useContext, useEffect, useState } from "react";
import apiClient from "../apiClient";

const HospitalContext = createContext(null);

export const HospitalProvider = ({ children }) => {
  const [hospital, setHospital] = useState(null);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);

  const fetchHospital = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/hospitals');
      setHospital(res.data);
    } catch (error) {
      console.error("Error fetching hospital:", error);
      setHospital(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchUser = async () => {
    try {
      if (localStorage.getItem('token')) {
        const res = await apiClient.get('/auth/me');
        setUser(res.data);
        await fetchHospital();
      } else {
        setUser(null);
        setHospital(null);
        setLoading(false);
      }
    } catch (e) {
      console.error("Auth me error:", e);
      setUser(null);
      setHospital(null);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
    const handleStorage = () => fetchUser();
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  return (
    <HospitalContext.Provider
      value={{
        hospital,
        loading,
        user,
        refreshHospital: fetchHospital,
        refreshUser: fetchUser
      }}
    >
      {children}
    </HospitalContext.Provider>
  );
};

export const useHospital = () => useContext(HospitalContext);
