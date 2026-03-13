import { defineStore } from "pinia"
import { ref, computed } from "vue"
import { usePOSSettingsStore } from "./posSettings"
import { db } from "../utils/offline/db"
import { logger } from "../utils/logger"
import { call } from "../utils/apiWrapper"

const log = logger.create("RestaurantStore")

export const useRestaurantStore = defineStore("restaurant", () => {
	const posSettingsStore = usePOSSettingsStore()

	// State
	const tables = ref([])
	const areas = ref([])
	const currentTableInvoice = ref(null)  // Running tab for selected table
	const isLoadingTable = ref(false)
	const isEnabled = computed(() => posSettingsStore.settings.enable_restaurant_mode)
	const defaultArea = computed(() => posSettingsStore.settings.default_restaurant_area)

	// Actions
	async function loadTablesAndAreas() {
		if (!isEnabled.value) return

		try {
			log.info("Loading tables and areas from local cache")
			areas.value = await db.restaurant_areas.toArray()
			tables.value = await db.restaurant_tables.toArray()
		} catch (error) {
			log.error("Failed to load tables from cache:", error)
		}
	}

	async function fetchFromNetwork() {
		if (!isEnabled.value) return

		try {
			log.info("Fetching tables from network")
			const res = await call("pos_next.api.restaurant.get_tables")

			if (res) {
				const { areas: fetchedAreas, tables: fetchedTables } = res

				// Update state
				areas.value = fetchedAreas || []
				tables.value = fetchedTables || []

				// Update offline cache
				await db.transaction("rw", db.restaurant_areas, db.restaurant_tables, async () => {
					await db.restaurant_areas.clear()
					if (areas.value.length) await db.restaurant_areas.bulkPut(areas.value)

					await db.restaurant_tables.clear()
					if (tables.value.length) await db.restaurant_tables.bulkPut(tables.value)
				})
			}
		} catch (error) {
			log.error("Failed to fetch tables from network:", error)
		}
	}

	async function updateTableStatus(tableName, status) {
		try {
			// Update local state and cache optimistically
			const table = tables.value.find(t => t.name === tableName)
			if (table) {
				table.status = status
				await db.restaurant_tables.put(table)
			}

			// Send to network
			if (navigator.onLine) {
				await call("pos_next.api.restaurant.update_table_status", {
					table_name: tableName,
					status
				})
			}
		} catch (error) {
			log.error(`Failed to update status for table ${tableName}:`, error)
		}
	}

	/**
	 * Get or create running tab (invoice) for table
	 * This implements the "Running Tab" pattern - one table = one open invoice
	 */
	async function getOrCreateTableInvoice(tableName, posProfile, customer = null) {
		if (!tableName) return null
		
		isLoadingTable.value = true
		try {
			log.info(`Getting running tab for table: ${tableName}`)
			
			const result = await call("pos_next.api.restaurant.get_or_create_table_invoice", {
				table_name: tableName,
				pos_profile: posProfile,
				customer: customer
			})
			
			if (result && result.success) {
				currentTableInvoice.value = {
					name: result.invoice_name,
					items: result.items || [],
					customer: result.customer,
					grandTotal: result.grand_total,
					isNew: result.is_new
				}
				log.info(`Table invoice loaded: ${result.invoice_name || 'NEW'}, items: ${result.items?.length || 0}`)
				return currentTableInvoice.value
			} else {
				log.error("Failed to get table invoice:", result?.message)
				return null
			}
		} catch (error) {
			log.error("Error getting table invoice:", error)
			return null
		} finally {
			isLoadingTable.value = false
		}
	}

	/**
	 * Merge new items to running tab
	 * Returns which items were actually sent to kitchen (new/additional)
	 */
	async function mergeItemsToInvoice(invoiceName, items, tableName) {
		if (!items?.length) return { success: true, sentItems: [] }
		
		try {
			log.info(`Merging ${items.length} items to invoice: ${invoiceName || 'NEW'}`)
			
			const result = await call("pos_next.api.restaurant.merge_items_to_invoice", {
				invoice_name: invoiceName,
				new_items: JSON.stringify(items),
				table_name: tableName
			})
			
			if (result && result.success) {
				// Update current invoice reference
				if (result.invoice_name) {
					currentTableInvoice.value = {
						...currentTableInvoice.value,
						name: result.invoice_name
					}
				}
				log.info(`Items merged successfully. New items sent: ${result.new_items_count}`)
				return {
					success: true,
					invoiceName: result.invoice_name,
					sentItems: result.sent_items || [],
					newItemsCount: result.new_items_count
				}
			} else {
				log.error("Failed to merge items:", result?.message)
				return { success: false, message: result?.message }
			}
		} catch (error) {
			log.error("Error merging items:", error)
			return { success: false, message: error.message }
		}
	}

	/**
	 * Close table invoice (process payment)
	 */
	async function closeTableInvoice(invoiceName, payments, writeOffAmount = 0) {
		try {
			log.info(`Closing table invoice: ${invoiceName}`)
			
			const result = await call("pos_next.api.restaurant.close_table_invoice", {
				invoice_name: invoiceName,
				payments: JSON.stringify(payments),
				write_off_amount: writeOffAmount
			})
			
			if (result && result.success) {
				// Clear current invoice
				currentTableInvoice.value = null
				log.info("Table invoice closed successfully")
			}
			
			return result
		} catch (error) {
			log.error("Error closing table invoice:", error)
			return { success: false, message: error.message }
		}
	}

	/**
	 * Clear current table invoice (when switching tables)
	 */
	function clearCurrentTableInvoice() {
		currentTableInvoice.value = null
	}

	/**
	 * Get table orders (legacy - for compatibility)
	 */
	async function getTableOrders(tableName) {
		try {
			if (!tableName) return []
			
			return await call("pos_next.api.restaurant.get_table_orders", {
				table_name: tableName
			})
		} catch (error) {
			log.error("Failed to get table orders:", error)
			return []
		}
	}

	return {
		tables,
		areas,
		isEnabled,
		defaultArea,
		currentTableInvoice,
		isLoadingTable,
		loadTablesAndAreas,
		fetchFromNetwork,
		updateTableStatus,
		getOrCreateTableInvoice,
		mergeItemsToInvoice,
		closeTableInvoice,
		clearCurrentTableInvoice,
		getTableOrders
	}
})
