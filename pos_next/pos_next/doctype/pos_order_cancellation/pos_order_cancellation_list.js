// List view settings for POS Order Cancellation
frappe.listview_settings['POS Order Cancellation'] = {
    get_indicator: function(doc) {
        const color_map = {
            'customer_changed_mind': 'blue',
            'wrong_item_ordered': 'orange',
            'item_out_of_stock': 'red',
            'long_preparation_time': 'yellow',
            'kitchen_mistake': 'red',
            'quality_issue': 'purple',
            'other': 'gray'
        };
        return [__(doc.reason_text), color_map[doc.reason] || 'gray'];
    },
    
    onload: function(listview) {
        listview.page.add_inner_button(__('View Report'), function() {
            frappe.set_route('query-report', 'Cancellation Report');
        });
    }
};
