import { shiftState } from "@/composables/useShift"
import { userResource } from "@/data/user"
import { createRouter, createWebHistory } from "vue-router"
import { session } from "./data/session"

const routes = [
	{
		path: "/",
		name: "POSSale",
		component: () => import("@/pages/POSSale.vue"),
	},
	{
		name: "Login",
		path: "/account/login",
		component: () => import("@/pages/Login.vue"),
	},
	{
		name: "KDS",
		path: "/kds",
		component: () => import("@/pages/KDS.vue"),
		meta: { requiresAuth: false }
	},
	{
		name: "CFD",
		path: "/cfd",
		component: () => import("@/pages/CFD.vue"),
		meta: { requiresAuth: false, allowGuest: true }
	},
	// Catch-all route
	{
		path: "/:pathMatch(.*)*",
		redirect: "/",
	},
]

const router = createRouter({
	history: createWebHistory("/pos"),
	routes,
})

router.beforeEach((to, from, next) => {
	// Check authentication status (session.user is already set in main.js before app mount)
	const isLoggedIn = session.isLoggedIn
	
	// Routes that don't require authentication
	const publicRoutes = ["Login", "KDS", "CFD"]
	const isPublicRoute = publicRoutes.includes(to.name)

	// Only log during development
	if (import.meta.env.DEV) {
		console.log(
			`[Router] ${to.name} (from: ${from.name || "initial"}), auth: ${isLoggedIn}, public: ${isPublicRoute}`,
		)
	}

	// Redirect logic
	if (to.name === "Login" && isLoggedIn) {
		next({ name: "POSSale" })
	} else if (!isPublicRoute && !isLoggedIn) {
		// Only require auth for non-public routes
		next({ name: "Login" })
	} else {
		next()
	}
})

export default router
