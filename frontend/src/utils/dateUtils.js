/**
 * Utility functions for date formatting
 */

/**
 * Format date to USA standard (MM/DD/YYYY)
 * @param {string|Date} date - Date string or Date object
 * @returns {string} Formatted date string
 */
export const formatDateUSA = (date) => {
  if (!date) return "N/A";
  
  try {
    const dateObj = new Date(date);
    if (isNaN(dateObj.getTime())) return "Invalid Date";
    
    return dateObj.toLocaleDateString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  } catch (error) {
    console.error('Error formatting date:', error);
    return "Invalid Date";
  }
};

/**
 * Format date with time to USA standard (MM/DD/YYYY HH:MM AM/PM)
 * @param {string|Date} date - Date string or Date object
 * @returns {string} Formatted date and time string
 */
export const formatDateTimeUSA = (date) => {
  if (!date) return "N/A";
  
  try {
    const dateObj = new Date(date);
    if (isNaN(dateObj.getTime())) return "Invalid Date";
    
    return dateObj.toLocaleDateString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  } catch (error) {
    console.error('Error formatting date and time:', error);
    return "Invalid Date";
  }
};

/**
 * Get today's date string for localStorage keys
 * @returns {string} Today's date string
 */
export const getTodayKey = () => {
  return new Date().toDateString();
};
