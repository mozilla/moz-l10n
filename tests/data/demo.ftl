# Simple string
title = About Localization

# Multiline string: press Shift + Enter to insert new line
feedbackUninstallCopy =
    Your participation in Firefox Test Pilot means
    a lot! Please check out our other experiments,
    and stay tuned for more to come.

# Attributes: in original string
emailOptInInput =
    .placeholder = email goes here :)

# Attributes: access keys
file-menu =
    .label = File
    .accesskey = F

other-file-menu =
    .aria-label = {file-menu.label}
    .accesskey = {file-menu.accesskey}

# Value and an attribute
shotIndexNoExpirationSymbol = ∞
    .title = This shot does not expire

# Plurals
delete-all-message =
    { $num ->
        [one] Delete this download?
       *[other] Delete { $num } downloads?
    }

# Plurals with custom values
delete-all-message-special-cases =
    { $num ->
        [1] Delete this download?
        [2] Delete this pair of downloads?
        [12] Delete this dozen of downloads?        
       *[other] Delete { $num } downloads?
    }

# DATETIME Built-in function
today-is = Today is { DATETIME($date, month: "long", year: "numeric", day: "numeric") }

# Soft Launch
default-content-process-count =
    .label = { $num } (default)

# PLATFORM() selector
platform = 
    { PLATFORM() ->
        [win] Options
       *[other] Preferences
    }

# NUMBER() selector
number =
    { NUMBER($var, type: "ordinal") ->
        [1] first
        [one] { $var }st
       *[other] { $var }nd
    }

# PLATFORM() selector in attribute
platform-attribute =
    .title = { PLATFORM() ->
        [win] Options
       *[other] Preferences
    }

# Double selector in attributes
download-choose-folder =
    .label =
        { PLATFORM() ->
            [macos] Choose…
           *[other] Browse…
        }
    .accesskey =
        { PLATFORM() ->
            [macos] e
           *[other] o
        }

# Multiple selectors
selector-multi =
   There { $num ->
       [one] is one email
      *[other] are many emails
   } for { $gender ->
      *[masculine] him
       [feminine] her
   }

# Term
-term = Term

# TermReference
term-reference = Term { -term } Reference

# StringExpression
string-expression = { "" }

# NumberExpression
number-expression = { 5 }

# MessageReference with attribute (was: AttributeExpression)
attribute-expression = { my_id.title }

# Nested selectors
selector-nested =
   { $gender ->
      *[feminine] { $num ->
           [one] There is one email for her
          *[other] There are many emails for her
       }
       [masculine] { $num ->
           [one] There is one email for him
          *[other] There are many emails for him
       }
   }
