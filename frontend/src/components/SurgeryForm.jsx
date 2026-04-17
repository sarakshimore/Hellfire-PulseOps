import React, { useEffect, useState } from "react";
import { PlusCircle } from "lucide-react";
import apiClient from "@/apiClient";
import { toast } from "sonner";
import { useHospital } from "@/context/HospitalContext";

const SurgeryForm = () => {
  const { hospital } = useHospital();

  const [surgeons, setSurgeons] = useState([]);

  const [formData, setFormData] = useState({
    patientName: "",
    surgeon: "",
    duration: "",
    scheduledDate: "",
    scheduledTime: "09:00",
    priority: "Normal",
  });

  // Fetch surgeons
  useEffect(() => {
    if (!hospital?.id) return;
    apiClient.get(`/hospitals/${hospital.id}/surgeons`).then((res) => {
      const list = res.data;
      setSurgeons(list);
      if (!formData.surgeon && list.length > 0) {
        setFormData((prev) => ({
          ...prev,
          surgeon: list[0].id,
        }));
      }
    }).catch(console.error);
  }, [hospital?.id]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  // Save request
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!hospital?.id) {
      toast.error("Hospital not loaded");
      return;
    }

    await apiClient.post(`/hospitals/${hospital.id}/surgery-requests`, {
      patientName: formData.patientName,
      surgeonId: formData.surgeon,
      preferredDate: formData.scheduledDate,
      surgeryType: "General",
      priority: formData.priority,
      status: "pending",
    });

    toast.success("Surgery added to queue");

   setFormData({
      patientName: "",
      surgeon: "",
      duration: "",
      scheduledDate: "",
      scheduledTime: "09:00",
      priority: "Normal",
    });
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <h3 className="font-bold text-slate-800 mb-6">Add Surgery Request</h3>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* PATIENT */}
        <div>
          <label className="block text-xs font-semibold text-slate-500 mb-1">
            Patient Name
          </label>
          <input
            type="text"
            name="patientName"
            value={formData.patientName}
            onChange={handleChange}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g. John Doe"
            required
          />
        </div>

        {/* SURGEON + DURATION */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1">
              Surgeon
            </label>
            <select
              name="surgeon"
              value={formData.surgeon}
              onChange={handleChange}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white text-slate-900"
              required
            >
              <option value="">Select Surgeon</option>
              {surgeons.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.specialization || s.department})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1">
              Duration (min)
            </label>
            <input
              type="number"
              name="duration"
              value={formData.duration}
              onChange={handleChange}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white text-slate-900"
              placeholder="60"
              required
            />
          </div>
        </div>

        {/* DATE + TIME */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1">
              Scheduled Date
            </label>
            <input
              type="date"
              name="scheduledDate"
              value={formData.scheduledDate}
              onChange={handleChange}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white text-slate-900"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1">
              Scheduled Time
            </label>
            <input
              type="time"
              name="scheduledTime"
              value={formData.scheduledTime}
              onChange={handleChange}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white text-slate-900"
              required
            />
          </div>
        </div>

        {/* PRIORITY */}
        <div>
          <label className="block text-xs font-semibold text-slate-500 mb-1">
            Priority
          </label>
          <select
            name="priority"
            value={formData.priority}
            onChange={handleChange}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white text-slate-900"
          >
            <option value="High">High</option>
            <option value="Normal">Normal</option>
            <option value="Elective">Elective</option>
          </select>
        </div>

        <button
          type="submit"
          className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg transition"
        >
          <PlusCircle size={18} />
          Add to Queue
        </button>
      </form>
    </div>
  );
};

export default SurgeryForm;
