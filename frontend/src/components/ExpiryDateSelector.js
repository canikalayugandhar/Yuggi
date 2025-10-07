import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Calendar, X, Plus } from "lucide-react";

const ExpiryDateSelector = ({ value = [], onChange, ...props }) => {
  const [newDate, setNewDate] = useState('');
  const [suggestedDates, setSuggestedDates] = useState([]);

  useEffect(() => {
    // Generate suggested expiry dates (Thursdays typically)
    const suggestions = [];
    const today = new Date();
    
    // Find next 8 Thursdays (typical expiry days)
    for (let i = 0; i < 60; i++) {
      const date = new Date(today);
      date.setDate(today.getDate() + i);
      
      // Check if it's Thursday (4) or the last Thursday of the month
      if (date.getDay() === 4) {
        const dateStr = date.toISOString().split('T')[0];
        suggestions.push({
          date: dateStr,
          label: date.toLocaleDateString('en-US', { 
            weekday: 'short', 
            month: 'short', 
            day: 'numeric' 
          }),
          isMonthly: isLastThursday(date)
        });
        
        if (suggestions.length >= 8) break;
      }
    }
    
    setSuggestedDates(suggestions);
  }, []);

  const isLastThursday = (date) => {
    const nextWeek = new Date(date);
    nextWeek.setDate(date.getDate() + 7);
    return nextWeek.getMonth() !== date.getMonth();
  };

  const handleAddDate = () => {
    if (newDate && !value.includes(newDate)) {
      const updatedDates = [...value, newDate].sort();
      onChange(updatedDates);
      setNewDate('');
    }
  };

  const handleRemoveDate = (dateToRemove) => {
    const updatedDates = value.filter(date => date !== dateToRemove);
    onChange(updatedDates);
  };

  const handleSuggestedDateClick = (suggestedDate) => {
    if (!value.includes(suggestedDate.date)) {
      const updatedDates = [...value, suggestedDate.date].sort();
      onChange(updatedDates);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddDate();
    }
  };

  return (
    <div className="space-y-4" {...props}>
      <div>
        <Label>Specific Expiry Dates (Optional)</Label>
        <div className="text-xs text-gray-500 mb-2">
          Select specific expiry dates to scan. Leave empty for auto-selection of nearest and weekly expiries.
        </div>
      </div>

      {/* Selected Dates */}
      {value.length > 0 && (
        <div className="space-y-2">
          <Label className="text-sm">Selected Dates:</Label>
          <div className="flex flex-wrap gap-2">
            {value.map((date) => (
              <Badge key={date} variant="secondary" className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {new Date(date + 'T00:00:00').toLocaleDateString('en-US', { 
                  weekday: 'short', 
                  month: 'short', 
                  day: 'numeric' 
                })}
                <button
                  onClick={() => handleRemoveDate(date)}
                  className="ml-1 hover:bg-red-200 rounded-full p-0.5"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Manual Date Input */}
      <div className="flex gap-2">
        <Input
          type="date"
          value={newDate}
          onChange={(e) => setNewDate(e.target.value)}
          onKeyPress={handleKeyPress}
          min={new Date().toISOString().split('T')[0]}
          placeholder="Select date"
          data-testid="manual-date-input"
          className="flex-1"
        />
        <Button
          type="button"
          onClick={handleAddDate}
          disabled={!newDate || value.includes(newDate)}
          size="sm"
          data-testid="add-date-btn"
        >
          <Plus className="w-4 h-4" />
        </Button>
      </div>

      {/* Suggested Expiry Dates */}
      <div className="space-y-2">
        <Label className="text-sm">Quick Select (Typical Expiry Thursdays):</Label>
        <div className="grid grid-cols-2 gap-2">
          {suggestedDates.map((suggestion) => (
            <Button
              key={suggestion.date}
              type="button"
              variant={value.includes(suggestion.date) ? "default" : "outline"}
              size="sm"
              onClick={() => handleSuggestedDateClick(suggestion)}
              disabled={value.includes(suggestion.date)}
              className="justify-start text-xs"
              data-testid={`suggested-date-${suggestion.date}`}
            >
              <Calendar className="w-3 h-3 mr-1" />
              {suggestion.label}
              {suggestion.isMonthly && (
                <Badge variant="secondary" className="ml-1 text-xs">Monthly</Badge>
              )}
            </Button>
          ))}
        </div>
      </div>

      {/* Clear All */}
      {value.length > 0 && (
        <Button
          type="button"
          variant="destructive"
          size="sm"
          onClick={() => onChange([])}
          data-testid="clear-all-dates-btn"
          className="w-full"
        >
          Clear All Selected Dates
        </Button>
      )}
    </div>
  );
};

export default ExpiryDateSelector;