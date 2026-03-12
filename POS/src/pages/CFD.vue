<template>
	<div class="flex flex-col h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 text-white overflow-hidden">
		<!-- Header -->
		<header class="bg-black/20 backdrop-blur-sm p-6 flex justify-between items-center">
			<div>
				<h1 class="text-3xl font-bold">{{ businessName }}</h1>
				<p class="text-blue-200">{{ __("Thank you for your order") }}</p>
			</div>
			<div class="text-right">
				<div class="text-4xl font-mono font-bold">{{ currentTime }}</div>
				<div class="text-blue-200">{{ currentDate }}</div>
			</div>
		</header>

		<!-- Main Content -->
		<main class="flex-1 flex items-center justify-center p-8">
			<!-- Waiting State -->
			<div v-if="currentOrder?.kds_status === 'Pending'" class="text-center">
				<div class="mb-8">
					<div class="w-32 h-32 mx-auto mb-6 rounded-full bg-yellow-500/20 flex items-center justify-center animate-pulse">
						<svg class="w-16 h-16 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
						</svg>
					</div>
					<h2 class="text-4xl font-bold mb-4">{{ __("Order Received") }}</h2>
					<p class="text-xl text-blue-200">{{ __("Your order is being prepared") }}</p>
				</div>
				<div class="text-6xl font-mono font-bold text-yellow-400">
					{{ elapsedTime }}
				</div>
			</div>

			<!-- Preparing State -->
			<div v-else-if="currentOrder?.kds_status === 'Preparing'" class="text-center">
				<div class="mb-8">
					<div class="w-32 h-32 mx-auto mb-6 rounded-full bg-blue-500/20 flex items-center justify-center animate-spin">
						<svg class="w-16 h-16 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/>
						</svg>
					</div>
					<h2 class="text-4xl font-bold mb-4">{{ __("Being Prepared") }}</h2>
					<p class="text-xl text-blue-200">{{ __("Our chefs are cooking your meal") }}</p>
				</div>
				<div class="text-6xl font-mono font-bold text-blue-400">
					{{ elapsedTime }}
				</div>
			</div>

			<!-- Ready State -->
			<div v-else-if="currentOrder?.kds_status === 'Ready'" class="text-center">
				<div class="mb-8">
					<div class="w-32 h-32 mx-auto mb-6 rounded-full bg-green-500/20 flex items-center justify-center animate-bounce">
						<svg class="w-16 h-16 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
						</svg>
					</div>
					<h2 class="text-5xl font-bold mb-4 text-green-400">{{ __("Order Ready!") }}</h2>
					<p class="text-2xl text-blue-200">{{ __("Please pick up your order") }}</p>
				</div>
				<div class="text-4xl font-bold">
					{{ __("Order #") }}{{ currentOrder?.name?.substring(-4) }}
				</div>
			</div>

			<!-- No Order State -->
			<div v-else class="text-center">
				<div class="w-32 h-32 mx-auto mb-6 rounded-full bg-white/10 flex items-center justify-center">
					<svg class="w-16 h-16 text-blue-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"/>
					</svg>
				</div>
				<h2 class="text-3xl font-bold mb-4">{{ __("Welcome") }}</h2>
				<p class="text-xl text-blue-200">{{ __("Place your order at the counter") }}</p>
			</div>
		</main>

		<!-- Footer - Order Items Preview -->
		<footer v-if="currentOrder?.items?.length" class="bg-black/30 backdrop-blur-sm p-6">
			<div class="max-w-4xl mx-auto">
				<h3 class="text-lg font-semibold mb-3 text-center">{{ __("Your Order") }}</h3>
				<div class="flex flex-wrap justify-center gap-4">
					<div 
						v-for="item in currentOrder.items" 
						:key="item.item_code"
						class="bg-white/10 backdrop-blur-sm rounded-lg px-4 py-2 flex items-center gap-3"
					>
						<span class="font-medium">{{ item.item_name }}</span>
						<span class="bg-white/20 rounded-full w-8 h-8 flex items-center justify-center font-bold">
							{{ item.qty }}
						</span>
					</div>
				</div>
			</div>
		</footer>
	</div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue"
import { useRoute } from "vue-router"
import { call } from "@/utils/apiWrapper"

const route = useRoute()
const currentOrder = ref(null)
const businessName = ref("Restaurant")
const pollInterval = ref(null)
const startTime = ref(null)

// Get order ID from URL query param
const orderId = computed(() => route.query.order)

// Current time
const currentTime = ref("")
const currentDate = ref("")

// Elapsed time since order creation
const elapsedTime = computed(() => {
	if (!startTime.value) return "00:00"
	const now = new Date()
	const diff = Math.floor((now - startTime.value) / 1000)
	const minutes = Math.floor(diff / 60)
	const seconds = diff % 60
	return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`
})

// Update clock
function updateClock() {
	const now = new Date()
	currentTime.value = now.toLocaleTimeString("az-AZ", { hour: "2-digit", minute: "2-digit" })
	currentDate.value = now.toLocaleDateString("az-AZ", { weekday: "long", year: "numeric", month: "long", day: "numeric" })
}

// Load order status
async function loadOrderStatus() {
	if (!orderId.value) return
	
	try {
		const res = await call("pos_next.api.restaurant.get_cfd_order", {
			order_id: orderId.value
		})
		
		if (res) {
			currentOrder.value = res
			if (res.creation && !startTime.value) {
				startTime.value = new Date(res.creation)
			}
		}
	} catch (error) {
		console.error("Failed to load CFD order:", error)
	}
}

onMounted(() => {
	updateClock()
	loadOrderStatus()
	
	// Update clock every second
	const clockInterval = setInterval(updateClock, 1000)
	
	// Poll for order updates every 5 seconds
	pollInterval.value = setInterval(loadOrderStatus, 5000)
	
	onUnmounted(() => {
		clearInterval(clockInterval)
		if (pollInterval.value) {
			clearInterval(pollInterval.value)
		}
	})
})

// Translation helper
const __ = (text) => text
</script>

<style scoped>
@keyframes pulse {
	0%, 100% { opacity: 1; }
	50% { opacity: 0.5; }
}

@keyframes bounce {
	0%, 100% { transform: translateY(0); }
	50% { transform: translateY(-10px); }
}

.animate-pulse {
	animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.animate-bounce {
	animation: bounce 1s infinite;
}
</style>
