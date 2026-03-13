<template>
	<div class="flex flex-col h-screen bg-gray-100 dark:bg-gray-900">
		<!-- Header -->
		<header class="bg-white dark:bg-gray-800 shadow-sm z-10 p-4 flex justify-between items-center">
			<div>
				<h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ __("Kitchen Display System") }}</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					{{ __("Active Orders") }}: {{ orders.length }} 
					<span v-if="socketConnected" class="text-green-500 ml-2">● {{ __("Live") }}</span>
					<span v-else class="text-orange-500 ml-2">○ {{ __("Offline") }}</span>
				</p>
			</div>
			<div class="flex gap-2">
				<Button @click="loadOrders" icon="refresh-cw" :loading="loading">
					{{ __("Refresh") }}
				</Button>
				<Button @click="$router.push('/')" variant="subtle">
					{{ __("Back to POS") }}
				</Button>
			</div>
		</header>

		<!-- Orders Grid -->
		<main class="flex-1 overflow-x-auto overflow-y-hidden p-6">
			<div v-if="loading && orders.length === 0" class="flex justify-center items-center h-full">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white"></div>
			</div>

			<div v-else-if="orders.length === 0" class="flex flex-col justify-center items-center h-full text-gray-500">
				<svg class="w-16 h-16 mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"></path></svg>
				<h2 class="text-xl font-medium">{{ __("No Active Orders") }}</h2>
				<p>{{ __("Kitchen is clear.") }}</p>
			</div>

			<div v-else class="flex gap-4 h-full overflow-x-auto snap-x">
				<KDSOrderCard
					v-for="order in sortedOrders"
					:key="order.name"
					:order="order"
					@status-updated="handleStatusUpdate"
					class="snap-start"
				/>
			</div>
		</main>
	</div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from "vue"
import { Button } from "frappe-ui"
import KDSOrderCard from "@/components/invoices/KDSOrderCard.vue"
import { call } from "@/utils/apiWrapper"
import { useToast } from "@/composables/useToast"
import { initSocket, useSocket } from "@/socket"

const { showError, showSuccess } = useToast()
const orders = ref([])
const loading = ref(true)
const socketConnected = ref(false)
let socket = null
let pollInterval = null

const sortedOrders = computed(() => {
	// Sort by creation time (oldest first)
	return [...orders.value].sort((a, b) => new Date(a.creation) - new Date(b.creation))
})

async function loadOrders() {
	try {
		loading.value = true
		const res = await call("pos_next.api.restaurant.get_kds_orders")
		
		if (res) {
			// Keep KDS-only orders (realtime orders not yet saved as POS Invoice)
			const kdsOnlyOrders = orders.value.filter(o => o.is_kds_only)
			// Merge backend orders with KDS-only orders
			orders.value = [...res, ...kdsOnlyOrders]
		}
	} catch (error) {
		console.error("Failed to load KDS orders:", error)
		showError(__("Failed to load orders from server."))
	} finally {
		loading.value = false
	}
}

function handleStatusUpdate() {
	showSuccess(__("Order status updated"))
	loadOrders()
}

// Socket.io realtime updates
function setupSocket() {
	console.log("[KDS] Setting up socket...")
	socket = initSocket()
	
	if (!socket) {
		console.warn("[KDS] Socket not available, falling back to polling")
		return false
	}
	
	console.log("[KDS] Socket object:", socket)
	
	// Connect socket
	console.log("[KDS] Calling socket.connect()...")
	socket.connect()
	
	socket.on("connect", () => {
		console.log("[KDS] ✅ Socket connected! ID:", socket.id)
		socketConnected.value = true
		
		// Join KDS room – this matches the room name used in restaurant.py realtime events
		console.log("[KDS] Joining kds_room...")
		socket.emit("join_kds_room")
	})
	
	socket.on("connect_error", (error) => {
		console.error("[KDS] ❌ Socket connection error:", error)
	})
	
	socket.on("disconnect", (reason) => {
		console.log("[KDS] Socket disconnected, reason:", reason)
		socketConnected.value = false
	})
	
	// Listen for ALL socket events (for debugging)
	socket.onAny((eventName, data) => {
		console.log(`[KDS] 📨 Socket event '${eventName}':`, data)
	})
	
	// Listen for new orders
	socket.on("kds_new_order", (data) => {
		console.log("[KDS] ✅ New order received:", data)
		// Play notification sound
		playNotificationSound()
		// Add order to local list (don't reload from backend - order is not saved as POS Invoice)
		const newOrder = {
			name: data.order_id,
			restaurant_table: data.table,
			kds_status: data.status || "Pending",
			items: data.items || [],
			creation: data.timestamp,
			is_kds_only: true  // Flag to identify KDS-only orders
		}
		orders.value.push(newOrder)
		// Sort by creation time
		orders.value.sort((a, b) => new Date(a.creation) - new Date(b.creation))
	})
	
	// Listen for status updates
	socket.on("kds_status_update", (data) => {
		console.log("[KDS] Status update received:", data)
		// Update specific order in the list
		const index = orders.value.findIndex(o => o.name === data.order_id)
		if (index !== -1) {
			orders.value[index].kds_status = data.status
				// Clear recently modified flag when status changes from Pending
				// This removes the red border/pulse animation
				if (data.status !== 'Pending') {
					orders.value[index].is_recently_modified = false
				}
		} else {
			// Order not in list, reload all
			loadOrders()
		}
	})
	
	// Listen for partial orders (new items added to existing order)
	socket.on("kds_partial_order", (data) => {
		console.log("[KDS] Partial order received:", data)
		const index = orders.value.findIndex(o => o.name === data.order_id)
		if (index !== -1) {
			// Existing order - mark as recently modified and update items
			orders.value[index].is_recently_modified = true
			orders.value[index].kds_status = "Pending"  // Reset to pending
			// Add new items to the order
			if (data.items) {
				for (const newItem of data.items) {
					const existingItem = orders.value[index].items.find(
						i => i.item_code === newItem.item_code
					)
					if (existingItem && newItem.is_additional) {
						existingItem.qty += newItem.qty
					} else {
						orders.value[index].items.push({
							item_code: newItem.item_code,
							item_name: newItem.item_name,
							qty: newItem.qty,
							posa_special_instructions: newItem.instructions
						})
					}
				}
			}
			// Play notification sound for reactivated orders
			if (data.is_reactivated) {
				playNotificationSound()
			}
		} else {
			// New order not in list, reload from backend
			loadOrders()
		}
	})
	
	// Listen for completed orders (remove from display)
	socket.on("kds_order_completed", (data) => {
		console.log("[KDS] Order completed:", data)
		orders.value = orders.value.filter(o => o.name !== data.order_id)
	})
}

function playNotificationSound() {
	try {
		const audio = new Audio("/assets/pos_next/sounds/order-notification.mp3")
		audio.volume = 0.5
		audio.play().catch(e => console.log("Audio play failed:", e))
	} catch (e) {
		console.log("Sound notification not available")
	}
}

onMounted(() => {
	// Initial load
	loadOrders()
	
	// Try socket first
	const socketWorks = setupSocket()
	
	// Fallback to polling if socket fails
	if (!socketWorks) {
		console.log("Using polling fallback for KDS")
		pollInterval = setInterval(loadOrders, 5000) // 5 seconds
	}
})

onUnmounted(() => {
	if (pollInterval) {
		clearInterval(pollInterval)
	}
	if (socket) {
		socket.off("kds_new_order")
		socket.off("kds_status_update")
		socket.off("kds_order_completed")
		socket.emit("leave_kds_room")
	}
})

// Translation helper
const __ = (text) => text
</script>

<style scoped>
/* Custom scrollbar for horizontal scrolling */
::-webkit-scrollbar {
	height: 12px;
}
::-webkit-scrollbar-track {
	background: rgba(0,0,0,0.05);
	border-radius: 6px;
}
::-webkit-scrollbar-thumb {
	background: rgba(0,0,0,0.2);
	border-radius: 6px;
}
</style>
