/*
 * Hello Minecraft! Launcher
 * Copyright (C) 2026 huangyuhui <huanghongxun2008@126.com> and contributors
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */
package org.jackhuang.hmcl.util;

import org.jackhuang.hmcl.util.i18n.LocaleUtils;
import org.jackhuang.hmcl.util.platform.NativeUtils;
import org.jackhuang.hmcl.util.platform.OperatingSystem;
import org.jackhuang.hmcl.util.platform.windows.Kernel32;
import org.jackhuang.hmcl.util.platform.windows.WinConstants;
import org.jetbrains.annotations.NotNullByDefault;
import org.jetbrains.annotations.Nullable;

import java.time.Duration;
import java.time.ZoneId;
import java.time.ZonedDateTime;

/// Region information for mirror selection and account defaults, without download restrictions.
@NotNullByDefault
public final class RegionUtils {

    /// Cached machine region; independent of the unrestricted download policy.
    private static final boolean IS_CHINA_MAINLAND_MACHINE = checkMachineIsChinaMainland();

    /// Keeps the upstream startup API without scheduling network requests.
    public static void init() {
        // This fork never queries the user's public IP to restrict downloads.
    }

    /// Detects the machine region using the upstream time zone and system region rules.
    private static boolean checkMachineIsChinaMainland() {
        if ("Asia/Shanghai".equals(ZoneId.systemDefault().getId()))
            return true;

        // Check if the time zone is UTC+8
        if (ZonedDateTime.now().getOffset().getTotalSeconds() == Duration.ofHours(8).toSeconds()) {
            if ("CN".equals(LocaleUtils.SYSTEM_DEFAULT.getCountry()))
                return true;

            if (OperatingSystem.CURRENT_OS == OperatingSystem.WINDOWS && NativeUtils.USE_JNA) {
                @Nullable Kernel32 kernel32 = Kernel32.INSTANCE;

                // https://learn.microsoft.com/windows/win32/intl/table-of-geographical-locations
                if (kernel32 != null && kernel32.GetUserGeoID(WinConstants.GEOCLASS_NATION) == 45) // China
                    return true;
            }
        }

        return false;
    }

    /// Returns the machine region for existing mirror and account behavior.
    public static boolean isIsChinaMainlandMachine() {
        return IS_CHINA_MAINLAND_MACHINE;
    }

    /// Always permits downloads, irrespective of machine region, IP, or network availability.
    public static boolean isIsChinaMainlandNetwork() {
        return false;
    }

    /// Prevents instantiation of this utility class.
    private RegionUtils() {
    }
}
