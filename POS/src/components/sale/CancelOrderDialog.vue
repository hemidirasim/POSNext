<!--
  CancelOrderDialog.vue - Order Cancellation Dialog with Reason Selection
  
  Features:
  - Predefined cancellation reasons
  - Custom reason input
  - Confirmation before cancellation
  - Tracks who cancelled and when
-->
<template>
	<Dialog
		:modelValue="show"
		@update:modelValue="$emit('update:show', $event)"
		:size="'sm'"
	>
		<template #header>
			<div class="flex items-center gap-2 text-red-600">
				<FeatherIcon name="x-circle" class="w-5 h-5" />
				<span class="font-semibold">{{ __('Cancel Order') }}</span>
			</div>
		</template>

		<div class="space-y-4">
			<!-- Warning Message -->
			<div class="bg-red-50 border border-red-200 rounded-lg p-3">
				<p class="text-sm text-red-700">
					{{ __('Are you sure you want to cancel this order?') }}
				</p>
				<p class="text-xs text-red-600 mt-1">
					{{ __('This action cannot be undone') }}
				</p>
			</div>

			<!-- Predefined Reasons -->
			<div>
				<label class="block text-sm font-medium text-gray-700 mb-2">
					{{ __('Cancellation Reason') }}
				</label>
				<div class="space-y-2">
					<button
						v-for="reason in predefinedReasons"
						:key="reason.value"
						type="button"
						@click="selectedReason = reason.value"
						:class="[
							'w-full text-left px-3 py-2 rounded-lg text-sm transition-colors',
							selectedReason === reason.value
								? 'bg-blue-100 text-blue-800 border border-blue-300'
								: 'bg-gray-50 text-gray-700 hover:bg-gray-100 border border-gray-200'
						]"
					>
						{{ reason.label }}
					</button>
				</div>
			</div>

			<!-- Custom Reason Input (shown when "Other" is selected) -->
			<div v-if="selectedReason === 'other'">
				<label class="block text-sm font-medium text-gray-700 mb-1">
					{{ __('Other Reason') }}
				</label>
				<FormControl
					type="textarea"
					v-model="customReason"
					:placeholder="__('Please specify reason')"
					rows="2"
				/>
			</div>
		</div>

		<template #actions>
			<Button
				variant="outline"
				@click="$emit('update:show', false)"
			>
				{{ __('Cancel') }}
			</Button>
			<Button
				variant="danger"
				@click="confirmCancel"
				:disabled="!canSubmit"
				:loading="isSubmitting"
			>
				{{ __('Confirm Cancellation') }}
			</Button>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Dialog, Button, FeatherIcon, FormControl } from 'frappe-ui'

const props = defineProps({
	show: {
		type: Boolean,
		default: false
	}
})

const emit = defineEmits(['update:show', 'confirm'])

// Predefined cancellation reasons
const predefinedReasons = [
	{ value: 'customer_changed_mind', label: __('Customer changed mind') },
	{ value: 'wrong_item_ordered', label: __('Wrong item ordered') },
	{ value: 'item_out_of_stock', label: __('Item out of stock') },
	{ value: 'long_preparation_time', label: __('Long preparation time') },
	{ value: 'kitchen_mistake', label: __('Kitchen mistake') },
	{ value: 'quality_issue', label: __('Quality issue') },
	{ value: 'other', label: __('Other Reason') }
]

const selectedReason = ref('')
const customReason = ref('')
const isSubmitting = ref(false)

const canSubmit = computed(() => {
	if (!selectedReason.value) return false
	if (selectedReason.value === 'other' && !customReason.value.trim()) return false
	return true
})

const confirmCancel = () => {
	if (!canSubmit.value) return
	
	const reason = selectedReason.value === 'other' 
		? customReason.value 
		: predefinedReasons.find(r => r.value === selectedReason.value)?.label
	
	emit('confirm', {
		reason: selectedReason.value,
		reasonText: reason,
		customNote: selectedReason.value === 'other' ? customReason.value : null
	})
	
	// Reset form
	selectedReason.value = ''
	customReason.value = ''
}
</script>
