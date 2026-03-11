<template>
	<Dialog
		v-model="show"
		:options="{ title: __('Select Delivery Address'), size: 'lg' }"
	>
		<template #body-content>
			<div class="flex flex-col gap-4">
				<!-- Customer Info -->
				<div v-if="customer" class="bg-blue-50 rounded-lg p-3">
					<div class="flex items-center gap-2">
						<svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
						</svg>
						<div>
							<p class="text-sm font-medium text-gray-900">{{ customer.customer_name }}</p>
							<p v-if="customer.mobile_no" class="text-xs text-gray-500">{{ customer.mobile_no }}</p>
						</div>
					</div>
				</div>

				<!-- Loading State -->
				<div v-if="loading" class="flex justify-center py-8">
					<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
				</div>

				<!-- No Addresses State -->
				<div v-else-if="addresses.length === 0" class="text-center py-8">
					<svg class="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
					</svg>
					<p class="text-gray-500 text-sm mb-4">{{ __('No addresses found for this customer') }}</p>
					<Button variant="solid" @click="showCreateForm = true">
						{{ __('Add New Address') }}
					</Button>
				</div>

				<!-- Address List -->
				<div v-else class="space-y-3">
					<p class="text-sm font-medium text-gray-700">{{ __('Select an address for delivery:') }}</p>
					
					<div
						v-for="address in addresses"
						:key="address.name"
						class="border rounded-lg p-4 cursor-pointer transition-all"
						:class="selectedAddress?.name === address.name 
							? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500' 
							: 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'"
						@click="selectAddress(address)"
					>
						<div class="flex items-start justify-between">
							<div class="flex items-start gap-3">
								<div class="mt-0.5">
									<div
										class="w-5 h-5 rounded-full border-2 flex items-center justify-center"
										:class="selectedAddress?.name === address.name 
											? 'border-blue-500 bg-blue-500' 
											: 'border-gray-300'"
									>
										<svg v-if="selectedAddress?.name === address.name" class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
											<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
										</svg>
									</div>
								</div>
								<div>
									<div class="flex items-center gap-2 mb-1">
										<span class="font-medium text-gray-900">{{ address.address_title }}</span>
										<span
											v-if="address.is_shipping_address"
											class="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded-full"
										>
											{{ __('Default') }}
										</span>
									</div>
									<p class="text-sm text-gray-600">{{ formatAddress(address) }}</p>
									<p v-if="address.phone" class="text-sm text-gray-500 mt-1">
										{{ __('Phone') }}: {{ address.phone }}
									</p>
								</div>
							</div>
						</div>
					</div>

					<!-- Add New Address Button -->
					<Button
						v-if="!showCreateForm"
						variant="ghost"
						class="w-full mt-2"
						@click="showCreateForm = true"
					>
						<template #prefix>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
							</svg>
						</template>
						{{ __('Add New Address') }}
					</Button>
				</div>

				<!-- Create New Address Form -->
				<div v-if="showCreateForm" class="border-t pt-4 mt-4">
					<h4 class="text-sm font-medium text-gray-900 mb-4">{{ __('Add New Address') }}</h4>
					
					<div class="space-y-4">
						<!-- Address Title -->
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">
								{{ __('Address Title') }} <span class="text-red-500">*</span>
							</label>
							<Input
								v-model="newAddress.address_title"
								type="text"
								:placeholder="__('e.g., Home, Office')"
							/>
						</div>

						<!-- Address Line 1 -->
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">
								{{ __('Address Line 1') }} <span class="text-red-500">*</span>
							</label>
							<Input
								v-model="newAddress.address_line1"
								type="text"
								:placeholder="__('Street address, P.O. box')"
							/>
						</div>

						<!-- Address Line 2 -->
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">
								{{ __('Address Line 2') }}
							</label>
							<Input
								v-model="newAddress.address_line2"
								type="text"
								:placeholder="__('Apartment, suite, unit, building, floor')"
							/>
						</div>

						<!-- City & County -->
						<div class="grid grid-cols-2 gap-3">
							<div>
								<label class="block text-sm font-medium text-gray-700 mb-1">
									{{ __('City') }} <span class="text-red-500">*</span>
								</label>
								<Input
									v-model="newAddress.city"
									type="text"
									:placeholder="__('City')"
								/>
							</div>
							<div>
								<label class="block text-sm font-medium text-gray-700 mb-1">
									{{ __('County/District') }}
								</label>
								<Input
									v-model="newAddress.county"
									type="text"
									:placeholder="__('County')"
								/>
							</div>
						</div>

						<!-- State & Pincode -->
						<div class="grid grid-cols-2 gap-3">
							<div>
								<label class="block text-sm font-medium text-gray-700 mb-1">
									{{ __('State/Province') }}
								</label>
								<Input
									v-model="newAddress.state"
									type="text"
									:placeholder="__('State')"
								/>
							</div>
							<div>
								<label class="block text-sm font-medium text-gray-700 mb-1">
									{{ __('Postal Code') }}
								</label>
								<Input
									v-model="newAddress.pincode"
									type="text"
									:placeholder="__('Postal code')"
								/>
							</div>
						</div>

						<!-- Phone -->
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">
								{{ __('Phone Number') }}
							</label>
							<Input
								v-model="newAddress.phone"
								type="tel"
								:placeholder="__('Contact phone for delivery')"
							/>
						</div>

						<!-- Default Address Checkbox -->
						<div class="flex items-center gap-2">
							<input
								id="is_shipping"
								v-model="newAddress.is_shipping_address"
								type="checkbox"
								class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
							/>
							<label for="is_shipping" class="text-sm text-gray-700">
								{{ __('Set as default shipping address') }}
							</label>
						</div>

						<!-- Form Actions -->
						<div class="flex gap-2 pt-2">
							<Button variant="outline" class="flex-1" @click="showCreateForm = false">
								{{ __('Cancel') }}
							</Button>
							<Button
								variant="solid"
								class="flex-1"
								:loading="saving"
								:disabled="!isFormValid"
								@click="saveAddress"
							>
								{{ __('Save Address') }}
							</Button>
						</div>
					</div>
				</div>

				<!-- Delivery Charge Info -->
				<div v-if="deliveryInfo.has_delivery" class="bg-amber-50 rounded-lg p-3 mt-4">
					<div class="flex items-start gap-2">
						<svg class="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
						<div>
							<p class="text-sm font-medium text-amber-900">{{ __('Delivery Information') }}</p>
							<p class="text-xs text-amber-700 mt-0.5">
								{{ deliveryInfo.is_free 
									? __('Free delivery applied!') 
									: __('Delivery charge') + ': ' + formatCurrency(deliveryInfo.charge) 
								}}
							</p>
						</div>
					</div>
				</div>
			</div>
		</template>

		<template #actions>
			<div class="flex gap-2">
				<Button variant="outline" class="flex-1" @click="close">
					{{ __('Cancel') }}
				</Button>
				<Button
					variant="solid"
					class="flex-1"
					:disabled="!selectedAddress"
					@click="confirmSelection"
				>
					{{ __('Confirm Delivery') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, computed, watch, inject } from 'vue'
import { createResource, Dialog, Button, Input } from 'frappe-ui'

const props = defineProps({
	modelValue: Boolean,
	customer: Object,
	cartTotal: Number,
	posProfile: String,
})

const emit = defineEmits(['update:modelValue', 'select', 'update:delivery-charge'])
const show = computed({
	get: () => props.modelValue,
	set: (val) => emit('update:modelValue', val),
})

const formatCurrency = inject('formatCurrency')

// State
const loading = ref(false)
const saving = ref(false)
const addresses = ref([])
const selectedAddress = ref(null)
const showCreateForm = ref(false)
const deliveryInfo = ref({ has_delivery: false, charge: 0 })

// New address form
const newAddress = ref({
	address_title: '',
	address_line1: '',
	address_line2: '',
	city: '',
	county: '',
	state: '',
	pincode: '',
	phone: '',
	is_shipping_address: true,
})

// Computed
const isFormValid = computed(() => {
	return newAddress.value.address_title?.trim() && 
		   newAddress.value.address_line1?.trim() && 
		   newAddress.value.city?.trim()
})

// Resources
const fetchAddresses = createResource({
	url: 'pos_next.api.delivery.get_customer_addresses',
	auto: false,
	onSuccess: (data) => {
		addresses.value = data || []
		// Auto-select default shipping address
		const defaultAddr = addresses.value.find(a => a.is_shipping_address)
		if (defaultAddr) {
			selectAddress(defaultAddr)
		}
	},
})

const calculateDelivery = createResource({
	url: 'pos_next.api.delivery.calculate_delivery_charge',
	auto: false,
	onSuccess: (data) => {
		deliveryInfo.value = data
		emit('update:delivery-charge', data)
	},
})

const saveAddressResource = createResource({
	url: 'pos_next.api.delivery.create_address',
	auto: false,
	onSuccess: (result) => {
		if (result.success) {
			// Refresh addresses
			loadAddresses()
			// Select the new address
			selectAddress(result.address)
			showCreateForm.value = false
			resetForm()
		}
	},
})

// Methods
async function loadAddresses() {
	if (!props.customer?.name) return
	
	loading.value = true
	try {
		await fetchAddresses.fetch({
			customer: props.customer.name,
		})
	} finally {
		loading.value = false
	}
}

async function updateDeliveryCharge() {
	if (!props.posProfile) return
	
	await calculateDelivery.fetch({
		customer: props.customer?.name,
		address_name: selectedAddress.value?.name,
		subtotal: props.cartTotal || 0,
		pos_profile: props.posProfile,
	})
}

function selectAddress(address) {
	selectedAddress.value = address
	updateDeliveryCharge()
}

function formatAddress(address) {
	const parts = [
		address.address_line1,
		address.address_line2,
		address.city,
		address.county,
		address.state,
		address.pincode,
	].filter(Boolean)
	return parts.join(', ')
}

async function saveAddress() {
	if (!isFormValid.value) return
	
	saving.value = true
	try {
		await saveAddressResource.fetch({
			address_data: {
				...newAddress.value,
				customer: props.customer?.name,
				address_type: 'Shipping',
			},
		})
	} finally {
		saving.value = false
	}
}

function resetForm() {
	newAddress.value = {
		address_title: '',
		address_line1: '',
		address_line2: '',
		city: '',
		county: '',
		state: '',
		pincode: '',
		phone: '',
		is_shipping_address: true,
	}
}

function confirmSelection() {
	if (!selectedAddress.value) return
	
	emit('select', {
		address: selectedAddress.value,
		deliveryInfo: deliveryInfo.value,
	})
	close()
}

function close() {
	show.value = false
	selectedAddress.value = null
	showCreateForm.value = false
	resetForm()
}

// Watch
watch(() => props.modelValue, (isOpen) => {
	if (isOpen && props.customer?.name) {
		loadAddresses()
		updateDeliveryCharge()
	}
})
</script>
