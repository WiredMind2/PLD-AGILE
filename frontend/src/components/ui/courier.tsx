import * as React from "react"

interface CourierProps {
  numCourier: number
  status: "Available" | "Busy" | "Offline"
  nbRequests: number
}

const Courier: React.FC<CourierProps> = ({numCourier, status, nbRequests}) => {
    const statusColor = status === "Available" ? "text-emerald-600" : "text-red-600"
    return (
        <div className="mb-4 space-y-2 bg-purple-50 dark:bg-purple-950/50 p-3 rounded-lg">
            <p className="text-sm font-medium text-purple-700 dark:text-purple-300">
                Courier {numCourier}
            </p>
            <div className="text-xs text-purple-600 dark:text-purple-400">
                Status:{" "}
                <span className={`${statusColor} font-medium`}>
                    {status}
                </span>{" "}
                • Requests: {nbRequests}
            </div>
        </div>
)}

export {Courier}