import * as React from "react"
import { User, Package } from "lucide-react"

interface CourierProps {
  numCourier: number
  status: "Available" | "Busy"
  nbRequests: number
}

const Courier: React.FC<CourierProps> = ({numCourier, status, nbRequests}) => {
    const statusColor = 
      status === "Available" 
        ? "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30" 
        : status === "Busy"
        ? "text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-950/30"
        : "text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-950/30"
    
    return (
        <div className="bg-purple-50 dark:bg-purple-950/50 p-3 rounded-lg border border-purple-100 dark:border-purple-900/50 hover:border-purple-300 dark:hover:border-purple-700 transition-colors">
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-purple-200 dark:bg-purple-800 flex items-center justify-center">
                        <User className="w-4 h-4 text-purple-700 dark:text-purple-300" />
                    </div>
                    <p className="text-sm font-semibold text-purple-900 dark:text-purple-100">
                        Courier {numCourier}
                    </p>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full font-medium ${statusColor}`}>
                    {status}
                </span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-purple-600 dark:text-purple-400 ml-10">
                <Package className="w-3.5 h-3.5" />
                <span>{nbRequests} request{nbRequests !== 1 ? 's' : ''}</span>
            </div>
        </div>
)}

export {Courier}