import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import RootLayout from '@/layouts/RootLayout'
import Home from '@/pages/HomeView'
import MainView from '@/pages/MainView'

const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    children: [
      { index: true, element: <Home /> },
      { path: 'main', element: <MainView /> },
    ]
  }
])

export default function App(): JSX.Element {
  return <RouterProvider router={router} />
}