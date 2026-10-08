package com.djdoom.itemesp.gui;

import net.minecraft.client.gui.widget.SliderWidget;
import net.minecraft.text.Text;

import java.util.function.IntConsumer;
import java.util.function.IntFunction;

/** Slider over an integer range that reports changes through a callback. */
final class IntSlider extends SliderWidget {
    private final String translationKey;
    private final int min;
    private final int max;
    private final IntFunction<String> formatter;
    private final IntConsumer onChange;

    IntSlider(int x, int y, int width, int height, String translationKey, int min, int max, int initial,
              IntFunction<String> formatter, IntConsumer onChange) {
        super(x, y, width, height, Text.empty(), toSliderValue(initial, min, max));
        this.translationKey = translationKey;
        this.min = min;
        this.max = max;
        this.formatter = formatter;
        this.onChange = onChange;
        updateMessage();
    }

    IntSlider(int x, int y, int width, int height, String translationKey, int min, int max, int initial,
              IntConsumer onChange) {
        this(x, y, width, height, translationKey, min, max, initial, String::valueOf, onChange);
    }

    private static double toSliderValue(int value, int min, int max) {
        return max == min ? 0.0 : (double) (Math.max(min, Math.min(max, value)) - min) / (max - min);
    }

    int current() {
        return min + (int) Math.round(value * (max - min));
    }

    @Override
    protected void updateMessage() {
        setMessage(Text.translatable(translationKey, formatter.apply(current())));
    }

    @Override
    protected void applyValue() {
        onChange.accept(current());
    }
}
