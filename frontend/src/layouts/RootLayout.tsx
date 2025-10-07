import { Outlet } from 'react-router-dom'

export default function RootLayout(): JSX.Element {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <main>
        <Outlet />
      </main>
    </div>
  )
}
