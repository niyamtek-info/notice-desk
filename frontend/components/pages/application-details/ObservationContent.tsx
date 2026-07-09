import React from "react";

const ObservationContent: React.FC = () => {
    return (
        <div className="bg-white p-8 rounded-lg shadow-sm h-full min-h-[500px] flex items-center justify-center">
            <div className="text-center text-gray-500">
                <h3 className="text-lg font-medium">Observation</h3>
                <p>No observations recorded yet.</p>
            </div>
        </div>
    );
};

export default ObservationContent;
