import { Bike, Sparkles, Route, MapPin } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useNavigate } from 'react-router-dom'
import { ThemeToggle } from '@/components/ui/theme-toggle'

export default function Home(): JSX.Element {
  const navigate = useNavigate()
  const onBegin = () => navigate('/main')

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-cyan-50 dark:from-blue-950 dark:via-purple-950 dark:to-cyan-950 flex items-center relative overflow-hidden">
      {/* Background decorative elements */}
            <div className="absolute top-4 right-4 z-10">
        <ThemeToggle />
      </div>
      <div className="absolute inset-0 opacity-20">
        <div className="absolute top-20 left-20 w-32 h-32 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full blur-3xl"></div>
        <div className="absolute bottom-20 right-20 w-40 h-40 bg-gradient-to-br from-purple-500 to-cyan-500 rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 left-1/3 w-24 h-24 bg-gradient-to-br from-cyan-500 to-blue-500 rounded-full blur-2xl"></div>
      </div>
      
      <div className="container mx-auto flex flex-col items-center justify-center text-center relative z-10">
        <div className="flex items-center gap-3 mb-8">
          <div className="rounded-full bg-gradient-to-r from-blue-500 to-purple-600 p-4 shadow-lg shadow-blue-500/25">
            <Bike className="h-8 w-8 text-white" aria-hidden />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Bike pickup & delivery GPS
            </span>
            <Sparkles className="h-4 w-4 text-purple-500" />
          </div>
        </div>

        <h1 className="text-4xl sm:text-6xl font-bold tracking-tight bg-gradient-to-r from-blue-600 via-purple-600 to-cyan-600 bg-clip-text text-transparent mb-2">
          Opti'tour
        </h1>
        
        <div className="flex items-center gap-2 mb-6">
          <Route className="h-5 w-5 text-blue-500" />
          <MapPin className="h-5 w-5 text-purple-500" />
          <Route className="h-5 w-5 text-cyan-500" />
        </div>
        
        <p className="mt-4 max-w-2xl text-balance text-gray-600 dark:text-gray-300 text-lg">
          Plan, pick up, and deliver with confidence using intelligent route optimization.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row gap-4">
          <Button 
            size="lg" 
            onClick={onBegin}
            className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white shadow-lg shadow-blue-500/25 hover:shadow-purple-500/25 transition-all duration-300 transform hover:scale-105"
          >
            <Sparkles className="mr-2 h-5 w-5" />
            Begin Your Journey
          </Button>
        </div>
      </div>
    </div>
  )
}
