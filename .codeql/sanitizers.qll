/**
 * @name Sanitization Functions
 * @description Custom sanitization functions that act as security barriers for sensitive data.
 * @kind sanitizer
 * @id python/custom-sanitizers
 */

import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.security.dataflow.ClearTextLogging

/**
 * A sanitizer for clear text logging of sensitive information.
 * This marks our custom sanitization functions as safe barriers.
 */
class CustomSanitizer extends ClearTextLogging::Sanitizer {
  CustomSanitizer() {
    this = any(Call call |
      call.getFunc().(Attribute).getName() in [
        "sanitize_for_logging",
        "sanitize_agent_id",
        "sanitize_client_id",
        "sanitize_cache_key",
        "sanitize_token",
        "sanitize_resource_uri",
        "secure_log_debug",
        "secure_log_info",
        "is_sanitized_for_logging"
      ] and
      call.getFunc().(Attribute).getObject().getName() = "security"
    )
    or
    this = any(Call call |
      call.getFunc().getName() in [
        "sanitize_for_logging",
        "sanitize_agent_id",
        "sanitize_client_id",
        "sanitize_cache_key",
        "sanitize_token",
        "sanitize_resource_uri",
        "secure_log_debug",
        "secure_log_info",
        "is_sanitized_for_logging"
      ]
    )
  }
}

/**
 * Mark sanitized logging functions as safe sinks for sensitive data.
 */
class SafeLoggingSink extends DataFlow::Node {
  SafeLoggingSink() {
    this = any(Call call |
      call.getFunc().(Attribute).getName() in ["secure_log_debug", "secure_log_info"] and
      call.getFunc().(Attribute).getObject().getName() = "security"
    )
  }
}
